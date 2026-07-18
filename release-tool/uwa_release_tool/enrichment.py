from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any


TRANSFORMATION_KEY = "nasa-202606-wws-code-enrichment"
TRANSFORMATION_NAME = "NASA 202606 WWS_Code metadata enrichment"
TRANSFORMATION_VERSION = "1.0.0"
TARGET_RUNID_PREFIX = "batch;;nasa-roses-202606-psbs;;"
JOIN_KEY = "WWS_Code"
COPY_FIELDS = (
    "PWS_ID",
    "SrcName",
    "PWS_Name",
    "County_Nam",
    "State",
    "HUC10_ID",
    "HUC10_Name",
    "WWS_Code",
    "SrcType",
    "Shape_Leng",
    "Shape_Area",
    "outlet_lon_lat",
)
LINEAGE_FIELDS = {
    "PWS_ID": "pws_id",
    "SrcName": "srcname",
    "PWS_Name": "pws_name",
    "County_Nam": "county_nam",
    "State": "state",
    "HUC10_ID": "huc10_id",
    "HUC10_Name": "huc10_name",
    "WWS_Code": "wws_code",
    "SrcType": "srctype",
    "Shape_Leng": "shape_leng",
    "Shape_Area": "shape_area",
    "outlet_lon_lat": "outlet_lon_lat",
}


class NasaEnrichmentError(RuntimeError):
    def __init__(self, code: str, message: str, *, count: int = 0):
        super().__init__(message)
        self.code = code
        self.count = count


@dataclass(frozen=True)
class NasaEnrichmentResult:
    document: dict[str, Any]
    matched: int
    target_unmatched: int
    source_unmatched: int
    duplicate: int
    source_runid_differences: int
    source_geometry_differences: int

    @property
    def unmatched(self) -> int:
        return self.target_unmatched + self.source_unmatched


def configuration() -> dict[str, Any]:
    return {
        "transformation_key": TRANSFORMATION_KEY,
        "version": TRANSFORMATION_VERSION,
        "target_runid_prefix": TARGET_RUNID_PREFIX,
        "join_key": JOIN_KEY,
        "join_key_authority": "target",
        "copy_fields": list(COPY_FIELDS),
        "runid_authority": "target",
        "geometry_authority": "target",
        "unmatched_target_fields": "explicit_null",
        "source_only_features": "report_only",
    }


def configuration_sha256() -> str:
    content = json.dumps(configuration(), separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(content).hexdigest()


def _features(document: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise NasaEnrichmentError("invalid-feature-collection", f"{label} is not a FeatureCollection")
    features = document.get("features")
    if not isinstance(features, list) or not features:
        raise NasaEnrichmentError("empty-feature-collection", f"{label} has no features")
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise NasaEnrichmentError("invalid-feature", f"{label} contains an invalid feature")
        if not isinstance(feature.get("properties"), dict):
            raise NasaEnrichmentError("invalid-properties", f"{label} feature properties are invalid")
    return features


def _join_index(features: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    index = {}
    duplicate_count = 0
    for feature in features:
        key = feature["properties"].get(JOIN_KEY)
        if not isinstance(key, str) or not key.strip():
            raise NasaEnrichmentError("missing-join-key", f"{label} feature has no WWS_Code")
        if key in index:
            duplicate_count += 1
        else:
            index[key] = feature
    if duplicate_count:
        raise NasaEnrichmentError(
            "duplicate-join-key",
            f"{label} contains duplicate WWS_Code values",
            count=duplicate_count,
        )
    return index


def _validate_target_runids(features: list[dict[str, Any]]) -> None:
    runids = []
    for feature in features:
        runid = feature["properties"].get("runid")
        if not isinstance(runid, str) or not runid.startswith(TARGET_RUNID_PREFIX):
            raise NasaEnrichmentError("invalid-target-runid", "target runid has the wrong NASA 202606 prefix")
        runids.append(runid)
    if len(runids) != len(set(runids)):
        raise NasaEnrichmentError("duplicate-target-runid", "target runids are not unique")


def _validate_source_fields(features: list[dict[str, Any]]) -> None:
    for feature in features:
        properties = feature["properties"]
        missing = [field for field in COPY_FIELDS if field not in properties]
        if missing:
            raise NasaEnrichmentError(
                "missing-source-field",
                "enrichment source is missing one or more approved fields",
                count=len(missing),
            )


def validate_preservation(target: dict[str, Any], output: dict[str, Any]) -> None:
    target_features = _features(target, "target")
    output_features = _features(output, "output")
    if len(target_features) != len(output_features):
        raise NasaEnrichmentError("member-count-changed", "enrichment changed target feature count")
    for target_feature, output_feature in zip(target_features, output_features, strict=True):
        target_properties = target_feature["properties"]
        output_properties = output_feature["properties"]
        if target_properties.get("runid") != output_properties.get("runid"):
            raise NasaEnrichmentError("runid-changed", "enrichment changed target runid or order")
        if target_feature.get("geometry") != output_feature.get("geometry"):
            raise NasaEnrichmentError("geometry-changed", "enrichment changed target geometry")
        if target_properties.get(JOIN_KEY) != output_properties.get(JOIN_KEY):
            raise NasaEnrichmentError("join-key-changed", "enrichment changed target WWS_Code")
        for field, value in target_properties.items():
            if field not in COPY_FIELDS and output_properties.get(field) != value:
                raise NasaEnrichmentError(
                    "target-property-changed",
                    "enrichment changed a non-enrichment target property",
                )


def enrich_nasa_202606(
    target: dict[str, Any],
    source: dict[str, Any],
) -> NasaEnrichmentResult:
    target_features = _features(target, "target")
    source_features = _features(source, "source")
    _validate_target_runids(target_features)
    target_index = _join_index(target_features, "target")
    source_index = _join_index(source_features, "source")
    _validate_source_fields(source_features)

    output = copy.deepcopy(target)
    matched = 0
    for output_feature in output["features"]:
        properties = output_feature["properties"]
        source_feature = source_index.get(properties[JOIN_KEY])
        if source_feature is None:
            for field in COPY_FIELDS:
                if field != JOIN_KEY:
                    properties[field] = None
            continue
        source_properties = source_feature["properties"]
        for field in COPY_FIELDS:
            existing = properties.get(field)
            incoming = source_properties[field]
            if existing is not None and existing != incoming:
                raise NasaEnrichmentError(
                    "conflicting-target-value",
                    "target and source provide conflicting enrichment values",
                )
            properties[field] = incoming
        matched += 1

    result = NasaEnrichmentResult(
        document=output,
        matched=matched,
        target_unmatched=len(target_index.keys() - source_index.keys()),
        source_unmatched=len(source_index.keys() - target_index.keys()),
        duplicate=0,
        source_runid_differences=sum(
            source_index[key]["properties"].get("runid")
            != target_index[key]["properties"]["runid"]
            for key in target_index.keys() & source_index.keys()
            if "runid" in source_index[key]["properties"]
        ),
        source_geometry_differences=sum(
            source_index[key].get("geometry") != target_index[key].get("geometry")
            for key in target_index.keys() & source_index.keys()
        ),
    )
    validate_preservation(target, result.document)
    return result


def lineage_field_decisions(target_sha256: str, source_sha256: str) -> list[dict[str, str]]:
    return [
        {"field": "runid", "authority": "target", "source_sha256": target_sha256},
        {"field": "geometry", "authority": "target", "source_sha256": target_sha256},
        {"field": "wws_code", "authority": "target", "source_sha256": target_sha256},
        *[
            {
                "field": LINEAGE_FIELDS[field],
                "authority": "source",
                "source_sha256": source_sha256,
            }
            for field in COPY_FIELDS
            if field != JOIN_KEY
        ],
    ]
