from __future__ import annotations

from typing import Any
from urllib.parse import quote

import pyarrow as pa
import pyarrow.parquet as pq
import requests

from server.watershed.legacy_runtime import legacy_parquet_path
from server.watershed.runtime_capabilities import (
    ResolvedCapability,
    RuntimeCapabilityError,
    fetch_verified_artifact,
)


class RhessysQueryError(RuntimeError):
    pass


def validate_query(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "kind",
        "scenario",
        "variable",
        "spatial_scale",
        "year",
    }:
        raise RhessysQueryError("RHESSys query shape is invalid")
    if value["kind"] not in {"choropleth", "time-series"}:
        raise RhessysQueryError("RHESSys query kind is unsupported")
    for field in ("scenario", "variable"):
        if not isinstance(value[field], str) or not value[field]:
            raise RhessysQueryError(f"RHESSys query {field} is invalid")
    if value["spatial_scale"] not in {"hillslope", "patch"}:
        raise RhessysQueryError("RHESSys query spatial scale is unsupported")
    year = value["year"]
    if year is not None and (
        not isinstance(year, int)
        or isinstance(year, bool)
        or not 1800 <= year <= 3000
    ):
        raise RhessysQueryError("RHESSys query year is invalid")
    if value["kind"] == "choropleth" and year is None:
        raise RhessysQueryError("RHESSys choropleth query requires a year")
    return value


def _materialized_dataset(
    capability: ResolvedCapability,
    query: dict[str, Any],
) -> dict[str, Any]:
    role = (
        query["spatial_scale"]
        if query["kind"] == "choropleth" or query["spatial_scale"] == "patch"
        else "basin"
    )
    matches = [
        item
        for item in capability.configuration["parquets"]
        if item["scenario"] == query["scenario"]
        and item["role"] == role
        and query["variable"] in {variable["id"] for variable in item["variables"]}
    ]
    if len(matches) != 1:
        raise RhessysQueryError("RHESSys query does not resolve one declared dataset")
    dataset = matches[0]
    if query["year"] is not None and not (
        dataset["year_range"][0] <= query["year"] <= dataset["year_range"][1]
    ):
        raise RhessysQueryError("RHESSys query year is outside the declared range")
    return dataset


def execute_materialized_query(
    capability: ResolvedCapability,
    value: Any,
) -> list[dict[str, int | float]]:
    query = validate_query(value)
    dataset = _materialized_dataset(capability, query)
    columns = ["year", query["variable"]]
    if query["kind"] == "choropleth":
        columns.append(dataset["spatial_id_field"])
    elif query["spatial_scale"] == "hillslope":
        columns.append("month")
    try:
        content = fetch_verified_artifact(dataset["artifact"])
        filters = [("year", "=", query["year"])] if query["year"] is not None else None
        table = pq.read_table(pa.BufferReader(content), columns=columns, filters=filters)
        frame = table.to_pandas()
    except (RuntimeCapabilityError, pa.ArrowException, KeyError) as error:
        raise RhessysQueryError("declared RHESSys Parquet is unavailable or invalid") from error
    if query["kind"] == "choropleth":
        grouped = (
            frame.groupby(dataset["spatial_id_field"], as_index=False)[query["variable"]]
            .mean()
            .sort_values(dataset["spatial_id_field"])
        )
        return [
            {
                "spatialId": int(row[dataset["spatial_id_field"]]),
                "value": float(row[query["variable"]]),
            }
            for _, row in grouped.iterrows()
        ]
    group_columns = ["year", "month"] if "month" in frame.columns else ["year"]
    grouped = frame.groupby(group_columns, as_index=False)[query["variable"]].mean()
    return [
        {
            "year": int(row["year"]),
            "month": int(row["month"]) if "month" in grouped.columns else 0,
            "day": 1,
            query["variable"]: float(row[query["variable"]]),
        }
        for _, row in grouped.iterrows()
    ]


def execute_legacy_query(runid: str, value: Any) -> list[dict[str, Any]]:
    query = validate_query(value)
    try:
        dataset_path, spatial_id = legacy_parquet_path(
            query["scenario"],
            query["spatial_scale"],
            query["variable"],
            query["kind"],
        )
    except KeyError as error:
        raise RhessysQueryError("legacy RHESSys query metadata is unsupported") from error
    alias = "d"
    if query["kind"] == "choropleth":
        payload = {
            "datasets": [{"alias": alias, "path": dataset_path}],
            "columns": [f"{alias}.{spatial_id} AS spatialId"],
            "filters": [{"column": f"{alias}.year", "operator": "=", "value": query["year"]}],
            "aggregations": [
                {"alias": "value", "expression": f"AVG({alias}.{query['variable']})"}
            ],
            "group_by": [f"{alias}.{spatial_id}"],
            "order_by": [f"{alias}.{spatial_id}"],
        }
    else:
        yearly = query["spatial_scale"] == "patch"
        group_by = [f"{alias}.year"] if yearly else [f"{alias}.year", f"{alias}.month"]
        payload = {
            "datasets": [{"alias": alias, "path": dataset_path}],
            "columns": [f"{alias}.year AS year"]
            + ([] if yearly else [f"{alias}.month AS month"]),
            "aggregations": [
                {
                    "alias": query["variable"],
                    "expression": f"AVG({alias}.{query['variable']})",
                }
            ],
            "group_by": group_by,
            "order_by": group_by,
        }
    endpoint = (
        "https://wepp.cloud/query-engine/runs/"
        f"{quote(runid, safe=';-._~')}/query"
    )
    try:
        response = requests.post(endpoint, json=payload, timeout=60)
        response.raise_for_status()
        document = response.json()
    except (requests.RequestException, ValueError) as error:
        raise RhessysQueryError("legacy RHESSys query endpoint is unavailable") from error
    if isinstance(document, list):
        return document
    if isinstance(document, dict):
        for key in ("records", "rows", "data"):
            if isinstance(document.get(key), list):
                return document[key]
    raise RhessysQueryError("legacy RHESSys query response is invalid")
