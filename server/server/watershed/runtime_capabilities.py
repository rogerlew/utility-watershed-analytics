from __future__ import annotations

import hashlib
import logging
import math
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests
from django.core.exceptions import ObjectDoesNotExist

from server.watershed.models import ActiveDataRelease, RunCapability, Watershed


logger = logging.getLogger("watershed.runtime_capabilities")

SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,95}$")
LEGACY_RHESSYS_MODES = {
    "aversive-forestry": RunCapability.Mode.DYNAMIC,
    "batch;;victoria-ca-2026-sbs;;Sooke09": RunCapability.Mode.PRECOMPUTED,
    "batch;;victoria-ca-2026-sbs;;Sooke15": RunCapability.Mode.PRECOMPUTED,
}


class RuntimeCapabilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResolvedCapability:
    capability_type: str
    runid: str
    state: str
    source: str
    available: bool
    mode: str | None = None
    durable_base_uri: str | None = None
    index_uri: str | None = None
    index_sha256: str | None = None
    geometry_revision: str | None = None
    access_policy: str | None = None
    configuration: dict[str, Any] | None = None


def _safe_https(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise RuntimeCapabilityError(f"{label} must be a bounded HTTPS URI")
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeCapabilityError(f"{label} must be a credential-free HTTPS URI")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise RuntimeCapabilityError(f"{label} must be a SHA-256")
    return value


def _string(value: Any, label: str, maximum: int = 255) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise RuntimeCapabilityError(f"{label} must be a bounded string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise RuntimeCapabilityError(f"{label} contains control characters")
    return value


def _key(value: Any, label: str) -> str:
    result = _string(value, label, 96)
    if not KEY_PATTERN.fullmatch(result):
        raise RuntimeCapabilityError(f"{label} is invalid")
    return result


def _finite_or_none(value: Any, label: str) -> int | float | None:
    if value is None:
        return None
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise RuntimeCapabilityError(f"{label} must be finite or null")
    return value


def _exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise RuntimeCapabilityError(f"{label} has missing or unexpected fields")
    return value


def _artifact(value: Any, base_uri: str, label: str) -> dict[str, Any]:
    value = _exact(
        value,
        {"uri", "sha256", "bytes", "media_type", "verified"},
        label,
    )
    uri = _safe_https(value["uri"], f"{label} uri")
    if not uri.startswith(base_uri.rstrip("/") + "/"):
        raise RuntimeCapabilityError(f"{label} is outside durable_base_uri")
    if (
        not isinstance(value["bytes"], int)
        or isinstance(value["bytes"], bool)
        or value["bytes"] <= 0
        or value["bytes"] > 10 * 1024 * 1024 * 1024
    ):
        raise RuntimeCapabilityError(f"{label} byte count is invalid")
    if value["verified"] is not True:
        raise RuntimeCapabilityError(f"{label} is not verified")
    return {
        "uri": uri,
        "sha256": _sha256(value["sha256"], f"{label} sha256"),
        "bytes": value["bytes"],
        "media_type": _string(value["media_type"], f"{label} media_type"),
        "verified": True,
    }


def _variables(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise RuntimeCapabilityError(f"{label} must be non-empty")
    variables = []
    for item in value:
        item = _exact(item, {"id", "label", "units"}, f"{label} variable")
        variables.append(
            {
                "id": _key(item["id"], "variable id"),
                "label": _string(item["label"], "variable label"),
                "units": _string(item["units"], "variable units", 64),
            }
        )
    if len({item["id"] for item in variables}) != len(variables):
        raise RuntimeCapabilityError(f"{label} contains duplicate variables")
    return variables


def _validate_rhessys_configuration(capability: RunCapability) -> dict[str, Any]:
    configuration = _exact(
        capability.runtime_configuration,
        {
            "schema_version",
            "enabled",
            "access_policy",
            "index_uri",
            "index_sha256",
            "geometry_revision",
            "scenarios",
            "variables",
            "spatial_inputs",
            "geotiffs",
            "parquets",
            "geometries",
        },
        "RHESSys runtime configuration",
    )
    if configuration["schema_version"] != 1:
        raise RuntimeCapabilityError("RHESSys runtime schema version is unsupported")
    if not isinstance(configuration["enabled"], bool):
        raise RuntimeCapabilityError("RHESSys enabled flag must be boolean")
    if configuration["access_policy"] not in {"public", "disabled"}:
        raise RuntimeCapabilityError("RHESSys access policy is unsupported")
    if configuration["index_uri"] != capability.index_uri:
        raise RuntimeCapabilityError("RHESSys index URI differs from its capability row")
    if configuration["index_sha256"] != capability.index_sha256:
        raise RuntimeCapabilityError("RHESSys index checksum differs from its capability row")
    geometry_revision = _sha256(
        configuration["geometry_revision"], "RHESSys geometry_revision"
    )
    base_uri = capability.durable_base_uri.rstrip("/") + "/"
    if not capability.index_uri.startswith(base_uri):
        raise RuntimeCapabilityError("RHESSys index is outside durable_base_uri")

    runtime_variables = _variables(configuration["variables"], "RHESSys runtime")
    variable_ids = {item["id"] for item in runtime_variables}
    raw_scenarios = configuration["scenarios"]
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise RuntimeCapabilityError("RHESSys scenarios must be non-empty")
    scenarios = []
    for item in raw_scenarios:
        item = _exact(
            item,
            {
                "id",
                "label",
                "description",
                "is_change",
                "variables",
                "year_range",
                "geometry_revision",
            },
            "RHESSys scenario",
        )
        scenario_variables = item["variables"]
        if not isinstance(scenario_variables, list) or not scenario_variables:
            raise RuntimeCapabilityError("RHESSys scenario variables must be non-empty")
        scenario_variables = [
            _key(value, "scenario variable") for value in scenario_variables
        ]
        if len(scenario_variables) != len(set(scenario_variables)):
            raise RuntimeCapabilityError("RHESSys scenario variables must be unique")
        years = item["year_range"]
        if (
            not isinstance(years, list)
            or len(years) != 2
            or any(not isinstance(year, int) or isinstance(year, bool) for year in years)
            or not 1800 <= years[0] <= years[1] <= 3000
        ):
            raise RuntimeCapabilityError("RHESSys scenario year range is invalid")
        scenario_geometry = _sha256(
            item["geometry_revision"], "scenario geometry_revision"
        )
        if scenario_geometry != geometry_revision:
            raise RuntimeCapabilityError("RHESSys scenario geometry revision differs")
        if not isinstance(item["is_change"], bool):
            raise RuntimeCapabilityError("RHESSys scenario is_change must be boolean")
        scenarios.append(
            {
                "id": _key(item["id"], "scenario id"),
                "label": _string(item["label"], "scenario label"),
                "description": _string(item["description"], "scenario description", 2048),
                "is_change": item["is_change"],
                "variables": scenario_variables,
                "year_range": years,
                "geometry_revision": scenario_geometry,
            }
        )
    if len({item["id"] for item in scenarios}) != len(scenarios):
        raise RuntimeCapabilityError("RHESSys scenario ids must be unique")
    scenario_ids = {item["id"] for item in scenarios}
    scenario_variables_by_id = {
        item["id"]: set(item["variables"]) for item in scenarios
    }
    declared_variables = {value for item in scenarios for value in item["variables"]}
    if not declared_variables.issubset(variable_ids):
        raise RuntimeCapabilityError("RHESSys scenario variable metadata is absent")

    raw_spatial = configuration["spatial_inputs"]
    if not isinstance(raw_spatial, list):
        raise RuntimeCapabilityError("RHESSys spatial inputs must be an array")
    spatial_inputs = []
    for item in raw_spatial:
        item = _exact(
            item,
            {"filename", "title", "artifact", "render", "geometry_revision"},
            "RHESSys spatial input",
        )
        render = _exact(
            item["render"],
            {"type", "min", "max", "unique_values", "group", "reversed"},
            "RHESSys spatial render metadata",
        )
        if render["type"] not in {"continuous", "categorical", "stream"}:
            raise RuntimeCapabilityError("RHESSys spatial render type is unsupported")
        if not isinstance(render["reversed"], bool):
            raise RuntimeCapabilityError("RHESSys spatial reversed flag must be boolean")
        minimum = _finite_or_none(render["min"], "RHESSys spatial minimum")
        maximum = _finite_or_none(render["max"], "RHESSys spatial maximum")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise RuntimeCapabilityError("RHESSys spatial render range is invalid")
        if render["type"] == "continuous" and (
            minimum is None or maximum is None
        ):
            raise RuntimeCapabilityError("RHESSys continuous render range is absent")
        unique_values = render["unique_values"]
        if unique_values is not None:
            if (
                not isinstance(unique_values, list)
                or not unique_values
                or len(unique_values) > 1024
            ):
                raise RuntimeCapabilityError(
                    "RHESSys spatial unique values are invalid"
                )
            unique_values = [
                _finite_or_none(value, "RHESSys spatial unique value")
                for value in unique_values
            ]
            if None in unique_values or len(unique_values) != len(set(unique_values)):
                raise RuntimeCapabilityError(
                    "RHESSys spatial unique values contain duplicates"
                )
        if render["type"] == "categorical" and unique_values is None:
            raise RuntimeCapabilityError("RHESSys categorical values are absent")
        group = render["group"]
        if group is not None:
            group = _string(group, "RHESSys spatial group", 96)
        revision = _sha256(item["geometry_revision"], "spatial geometry_revision")
        if revision != geometry_revision:
            raise RuntimeCapabilityError("RHESSys spatial geometry revision differs")
        spatial_inputs.append(
            {
                "filename": _string(item["filename"], "spatial filename"),
                "title": _string(item["title"], "spatial title"),
                "artifact": _artifact(item["artifact"], base_uri, "spatial artifact"),
                "render": {
                    "type": render["type"],
                    "min": minimum,
                    "max": maximum,
                    "unique_values": unique_values,
                    "group": group,
                    "reversed": render["reversed"],
                },
                "geometry_revision": revision,
            }
        )
    if len({item["filename"] for item in spatial_inputs}) != len(spatial_inputs):
        raise RuntimeCapabilityError("RHESSys spatial filenames must be unique")

    raw_geotiffs = configuration["geotiffs"]
    if not isinstance(raw_geotiffs, list):
        raise RuntimeCapabilityError("RHESSys geotiffs must be an array")
    geotiffs = []
    for item in raw_geotiffs:
        item = _exact(
            item,
            {"scenario", "variable", "artifact", "value_range", "geometry_revision"},
            "RHESSys geotiff",
        )
        scenario = _key(item["scenario"], "geotiff scenario")
        variable = _key(item["variable"], "geotiff variable")
        if (
            scenario not in scenario_ids
            or variable not in scenario_variables_by_id[scenario]
        ):
            raise RuntimeCapabilityError("RHESSys geotiff has undeclared metadata")
        value_range = item["value_range"]
        if value_range is not None:
            value_range = _exact(value_range, {"min", "max"}, "geotiff value range")
            if any(
                not isinstance(value_range[key], (int, float))
                or isinstance(value_range[key], bool)
                or not math.isfinite(value_range[key])
                for key in ("min", "max")
            ) or value_range["min"] > value_range["max"]:
                raise RuntimeCapabilityError("RHESSys geotiff value range is invalid")
        revision = _sha256(item["geometry_revision"], "geotiff geometry_revision")
        if revision != geometry_revision:
            raise RuntimeCapabilityError("RHESSys geotiff geometry revision differs")
        geotiffs.append(
            {
                "scenario": scenario,
                "variable": variable,
                "artifact": _artifact(item["artifact"], base_uri, "geotiff artifact"),
                "value_range": value_range,
                "geometry_revision": revision,
            }
        )
    geotiff_pairs = [(item["scenario"], item["variable"]) for item in geotiffs]
    if len(geotiff_pairs) != len(set(geotiff_pairs)):
        raise RuntimeCapabilityError("RHESSys geotiff pairs must be unique")

    raw_parquets = configuration["parquets"]
    if not isinstance(raw_parquets, list):
        raise RuntimeCapabilityError("RHESSys parquets must be an array")
    parquets = []
    for item in raw_parquets:
        item = _exact(
            item,
            {
                "dataset_key",
                "scenario",
                "role",
                "artifact",
                "spatial_id_field",
                "variables",
                "year_range",
                "geometry_revision",
            },
            "RHESSys parquet",
        )
        scenario = _key(item["scenario"], "parquet scenario")
        if scenario not in scenario_ids:
            raise RuntimeCapabilityError("RHESSys parquet scenario is undeclared")
        if item["role"] not in {"basin", "hillslope", "patch"}:
            raise RuntimeCapabilityError("RHESSys parquet role is unsupported")
        parquet_variables = _variables(item["variables"], "RHESSys parquet")
        if not {value["id"] for value in parquet_variables}.issubset(
            scenario_variables_by_id[scenario]
        ):
            raise RuntimeCapabilityError("RHESSys parquet variable is undeclared")
        years = item["year_range"]
        if (
            not isinstance(years, list)
            or len(years) != 2
            or any(not isinstance(year, int) or isinstance(year, bool) for year in years)
            or not 1800 <= years[0] <= years[1] <= 3000
        ):
            raise RuntimeCapabilityError("RHESSys parquet year range is invalid")
        revision = _sha256(item["geometry_revision"], "parquet geometry_revision")
        if revision != geometry_revision:
            raise RuntimeCapabilityError("RHESSys parquet geometry revision differs")
        parquets.append(
            {
                "dataset_key": _key(item["dataset_key"], "parquet dataset_key"),
                "scenario": scenario,
                "role": item["role"],
                "artifact": _artifact(item["artifact"], base_uri, "parquet artifact"),
                "spatial_id_field": _key(item["spatial_id_field"], "spatial id field"),
                "variables": parquet_variables,
                "year_range": years,
                "geometry_revision": revision,
            }
        )
    if len({item["dataset_key"] for item in parquets}) != len(parquets):
        raise RuntimeCapabilityError("RHESSys parquet dataset keys must be unique")
    parquet_coordinates = [
        (item["scenario"], item["role"], variable["id"])
        for item in parquets
        for variable in item["variables"]
    ]
    if len(parquet_coordinates) != len(set(parquet_coordinates)):
        raise RuntimeCapabilityError("RHESSys parquet query coordinates overlap")

    raw_geometries = configuration["geometries"]
    if not isinstance(raw_geometries, list):
        raise RuntimeCapabilityError("RHESSys geometries must be an array")
    geometries = []
    for item in raw_geometries:
        item = _exact(
            item,
            {"scale", "scenarios", "artifact", "source_crs", "geometry_revision"},
            "RHESSys geometry",
        )
        if item["scale"] not in {"hillslope", "patch"}:
            raise RuntimeCapabilityError("RHESSys geometry scale is unsupported")
        geometry_scenarios = item["scenarios"]
        if not isinstance(geometry_scenarios, list) or not geometry_scenarios:
            raise RuntimeCapabilityError("RHESSys geometry scenarios must be non-empty")
        geometry_scenarios = [_key(value, "geometry scenario") for value in geometry_scenarios]
        if not set(geometry_scenarios).issubset(scenario_ids):
            raise RuntimeCapabilityError("RHESSys geometry scenario is undeclared")
        revision = _sha256(item["geometry_revision"], "geometry geometry_revision")
        if revision != geometry_revision:
            raise RuntimeCapabilityError("RHESSys geometry revision differs")
        source_crs = _string(item["source_crs"], "geometry source CRS", 16)
        if not re.fullmatch(r"EPSG:[0-9]{4,6}", source_crs):
            raise RuntimeCapabilityError("RHESSys geometry source CRS is invalid")
        geometries.append(
            {
                "scale": item["scale"],
                "scenarios": geometry_scenarios,
                "artifact": _artifact(item["artifact"], base_uri, "geometry artifact"),
                "source_crs": source_crs,
                "geometry_revision": revision,
            }
        )
    geometry_coordinates = [
        (item["scale"], scenario)
        for item in geometries
        for scenario in item["scenarios"]
    ]
    if len(geometry_coordinates) != len(set(geometry_coordinates)):
        raise RuntimeCapabilityError("RHESSys geometry coordinates overlap")

    if capability.mode in {RunCapability.Mode.DYNAMIC, RunCapability.Mode.BOTH}:
        if not spatial_inputs or not parquets or not geometries:
            raise RuntimeCapabilityError("RHESSys dynamic mode lacks declared assets")
        required_geometry = {
            (item["role"], item["scenario"])
            for item in parquets
            if item["role"] in {"hillslope", "patch"}
        }
        if not required_geometry.issubset(set(geometry_coordinates)):
            raise RuntimeCapabilityError("RHESSys query geometry is undeclared")
    if capability.mode in {RunCapability.Mode.PRECOMPUTED, RunCapability.Mode.BOTH}:
        expected_pairs = {
            (scenario["id"], variable)
            for scenario in scenarios
            for variable in scenario["variables"]
        }
        if set(geotiff_pairs) != expected_pairs:
            raise RuntimeCapabilityError("RHESSys precomputed scenario coverage differs")

    return {
        **configuration,
        "geometry_revision": geometry_revision,
        "scenarios": scenarios,
        "variables": runtime_variables,
        "spatial_inputs": spatial_inputs,
        "geotiffs": geotiffs,
        "parquets": parquets,
        "geometries": geometries,
    }


def _validate_sbs_configuration(capability: RunCapability) -> dict[str, Any]:
    configuration = _exact(
        capability.runtime_configuration,
        {
            "schema_version",
            "enabled",
            "access_policy",
            "index_uri",
            "index_sha256",
            "geometry_revision",
            "artifact",
        },
        "SBS runtime configuration",
    )
    if configuration["schema_version"] != 1:
        raise RuntimeCapabilityError("SBS runtime schema version is unsupported")
    if not isinstance(configuration["enabled"], bool):
        raise RuntimeCapabilityError("SBS enabled flag must be boolean")
    if configuration["access_policy"] not in {"public", "disabled"}:
        raise RuntimeCapabilityError("SBS access policy is unsupported")
    if configuration["index_uri"] != capability.index_uri:
        raise RuntimeCapabilityError("SBS index URI differs from its capability row")
    if configuration["index_sha256"] != capability.index_sha256:
        raise RuntimeCapabilityError("SBS index checksum differs from its capability row")
    base_uri = capability.durable_base_uri.rstrip("/") + "/"
    if not capability.index_uri.startswith(base_uri):
        raise RuntimeCapabilityError("SBS index is outside durable_base_uri")
    return {
        **configuration,
        "geometry_revision": _sha256(
            configuration["geometry_revision"], "SBS geometry_revision"
        ),
        "artifact": _artifact(configuration["artifact"], base_uri, "SBS artifact"),
    }


def validate_runtime_configuration(capability: RunCapability) -> dict[str, Any]:
    if capability.capability_type == RunCapability.CapabilityType.RHESSYS:
        return _validate_rhessys_configuration(capability)
    if capability.capability_type == RunCapability.CapabilityType.SBS:
        if capability.mode != RunCapability.Mode.PRECOMPUTED:
            raise RuntimeCapabilityError("SBS capability mode must be precomputed")
        return _validate_sbs_configuration(capability)
    raise RuntimeCapabilityError("capability type is unsupported")


def _active_pointer() -> ActiveDataRelease:
    try:
        return ActiveDataRelease.objects.select_related("release").get(singleton_id=1)
    except ObjectDoesNotExist as error:
        raise RuntimeCapabilityError("active release singleton is missing") from error


def _legacy_rhessys(runid: str, state: str) -> ResolvedCapability:
    mode = LEGACY_RHESSYS_MODES.get(runid)
    if mode is None:
        return ResolvedCapability("rhessys", runid, state, "none", False)
    logger.info(
        "capability.legacy_fallback capability_type=rhessys runid=%s mode=%s",
        runid,
        mode,
    )
    return ResolvedCapability(
        "rhessys",
        runid,
        state,
        "legacy-empty",
        True,
        mode=mode,
        access_policy="public",
    )


def _legacy_sbs(runid: str, state: str) -> ResolvedCapability:
    if not Watershed.objects.filter(runid=runid).exists():
        return ResolvedCapability("sbs", runid, state, "none", False)
    logger.info(
        "capability.legacy_fallback capability_type=sbs runid=%s mode=precomputed",
        runid,
    )
    return ResolvedCapability(
        "sbs",
        runid,
        state,
        "legacy-empty",
        True,
        mode=RunCapability.Mode.PRECOMPUTED,
        access_policy="public",
    )


def resolve_capability(runid: str, capability_type: str) -> ResolvedCapability:
    active = _active_pointer()
    if active.state == ActiveDataRelease.State.EMPTY:
        if capability_type == RunCapability.CapabilityType.RHESSYS:
            return _legacy_rhessys(runid, active.state)
        if capability_type == RunCapability.CapabilityType.SBS:
            return _legacy_sbs(runid, active.state)
        return ResolvedCapability(capability_type, runid, active.state, "none", False)

    capability = (
        RunCapability.objects.filter(
            run_state__release=active.release,
            run_state__runid=runid,
            capability_type=capability_type,
        )
        .select_related("run_state")
        .first()
    )
    if capability is None:
        return ResolvedCapability(capability_type, runid, active.state, "none", False)
    try:
        configuration = validate_runtime_configuration(capability)
    except RuntimeCapabilityError as error:
        logger.error(
            "capability.configuration_rejected capability_type=%s runid=%s reason=%s",
            capability_type,
            runid,
            error,
        )
        return ResolvedCapability(capability_type, runid, active.state, "invalid", False)
    available = configuration["enabled"] and configuration["access_policy"] == "public"
    return ResolvedCapability(
        capability_type,
        runid,
        active.state,
        "materialized",
        available,
        mode=capability.mode,
        durable_base_uri=capability.durable_base_uri,
        index_uri=capability.index_uri,
        index_sha256=capability.index_sha256,
        geometry_revision=configuration["geometry_revision"],
        access_policy=configuration["access_policy"],
        configuration=configuration if available else None,
    )


def fetch_verified_artifact(reference: dict[str, Any], *, timeout: int = 60) -> bytes:
    expected_size = reference["bytes"]
    digest = hashlib.sha256()
    content = bytearray()
    try:
        with requests.get(reference["uri"], timeout=timeout, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                content.extend(chunk)
                digest.update(chunk)
                if len(content) > expected_size:
                    raise RuntimeCapabilityError("artifact exceeds its declared byte count")
    except requests.RequestException as error:
        raise RuntimeCapabilityError("declared artifact is unavailable") from error
    if len(content) != expected_size or digest.hexdigest() != reference["sha256"]:
        raise RuntimeCapabilityError("declared artifact size or checksum differs")
    return bytes(content)


def capability_summary(runid: str) -> dict[str, Any]:
    result = {}
    for capability_type in (
        RunCapability.CapabilityType.RHESSYS,
        RunCapability.CapabilityType.SBS,
    ):
        resolved = resolve_capability(runid, capability_type)
        summary = {
            "available": resolved.available,
            "source": resolved.source,
            "mode": resolved.mode,
            "access_policy": resolved.access_policy,
            "index_uri": resolved.index_uri,
            "index_sha256": resolved.index_sha256,
            "geometry_revision": resolved.geometry_revision,
        }
        if resolved.configuration and capability_type == RunCapability.CapabilityType.RHESSYS:
            summary["scenarios"] = resolved.configuration["scenarios"]
            summary["variables"] = resolved.configuration["variables"]
        else:
            summary["scenarios"] = []
            summary["variables"] = []
        result[capability_type] = summary
    return {"state": _active_pointer().state, **result}
