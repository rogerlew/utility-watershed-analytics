#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable


FINGERPRINT_VERSION = 1


class FingerprintError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise FingerprintError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_float=Decimal,
        object_pairs_hook=unique_object,
    )


def canonical_decimal(value: Decimal | int) -> str:
    decimal_value = value if isinstance(value, Decimal) else Decimal(value)
    if not decimal_value.is_finite():
        raise FingerprintError("non-finite numbers are not canonical")
    if decimal_value == 0:
        return "0"
    rendered = format(decimal_value.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, float):
        raise FingerprintError("binary floating-point values are prohibited")
    if isinstance(value, (int, Decimal)):
        return canonical_decimal(value)
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [canonical_value(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise FingerprintError("object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise FingerprintError(f"object key normalization collision: {normalized_key}")
            normalized[normalized_key] = canonical_value(item)
        return normalized
    raise FingerprintError(f"unsupported canonical type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    normalized = canonical_value(value)
    rendered = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{rendered}\n".encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def artifact_content(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "sha256": artifact["sha256"],
        "bytes": artifact["bytes"],
        "media_type": artifact["media_type"],
    }


def normalize_artifact(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "fingerprint_version": FINGERPRINT_VERSION,
        "subject": "artifact",
        "content": artifact_content(document),
    }


def normalize_capability(document: dict[str, Any]) -> dict[str, Any]:
    scenarios = [
        {"key": item["key"], "variables": sorted(item["variables"])}
        for item in document["scenarios"]
    ]
    scenarios.sort(key=lambda item: item["key"])
    spatial_inputs = [
        {
            "role": item["role"],
            "artifact": artifact_content(item["artifact"]),
            "required_for_activation": item["required_for_activation"],
        }
        for item in document["spatial_inputs"]
    ]
    spatial_inputs.sort(key=lambda item: item["role"])

    parquets = [
        {
            "role": item["role"],
            "artifact": artifact_content(item["artifact"]),
            "spatial_id_field": item["spatial_id_field"],
            "columns": sorted(item["columns"], key=lambda column: column["name"]),
            "variables": sorted(item["variables"], key=lambda variable: variable["name"]),
            "year_range": item["year_range"],
            "required_for_activation": item["required_for_activation"],
        }
        for item in document["parquets"]
    ]
    parquets.sort(key=lambda item: item["role"])

    geotiffs = [
        {
            "scenario": item["scenario"],
            "variable": item["variable"],
            "artifact": artifact_content(item["artifact"]),
            "crs": item["crs"],
            "bounds": item["bounds"],
            "dimensions": item["dimensions"],
            "bands": item["bands"],
            "nodata": item["nodata"],
            "required_for_activation": item["required_for_activation"],
        }
        for item in document["geotiffs"]
    ]
    geotiffs.sort(
        key=lambda item: (
            item["scenario"],
            item["variable"],
            item["artifact"]["sha256"],
        )
    )

    return {
        "fingerprint_version": FINGERPRINT_VERSION,
        "subject": "capability",
        "collection_key": document["collection_key"],
        "watershed_key": document["watershed_key"],
        "runid": document["runid"],
        "mode": document["mode"],
        "durable_base_uri": document["durable_base_uri"],
        "geometry_revision": document["geometry_revision"],
        "scenarios": scenarios,
        "spatial_inputs": spatial_inputs,
        "parquets": parquets,
        "geotiffs": geotiffs,
    }


def normalize_run(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "fingerprint_version": FINGERPRINT_VERSION,
        "subject": "run",
        "collection_key": document["collection_key"],
        "watershed_key": document["watershed_key"],
        "runid": document["runid"],
        "display_name": document["display_name"],
        "aliases": sorted(document["aliases"]),
        "artifact_fingerprints": document["artifact_fingerprints"],
        "transformation_lineage_fingerprint": document.get(
            "transformation_lineage_fingerprint"
        ),
        "rhessys_index_fingerprint": document.get("rhessys_index_fingerprint"),
        "expected": document["expected"],
        "capability_fingerprint": document.get("capability_fingerprint"),
    }


def normalize_domain(document: dict[str, Any]) -> dict[str, Any]:
    runs = [dict(run) for run in document["runs"]]
    runs.sort(key=lambda run: (run["collection_key"], run["watershed_key"], run["runid"]))
    return {
        "fingerprint_version": FINGERPRINT_VERSION,
        "subject": "watershed-domain",
        "runs": runs,
    }


def normalize_release(document: dict[str, Any]) -> dict[str, Any]:
    compatibility = document["compatibility"]
    collections = []
    for collection in document["collections"]:
        source = collection["source"]
        collections.append(
            {
                "collection_key": collection["collection_key"],
                "display_name": collection["display_name"],
                "source": {
                    "kind": source["kind"],
                    "source_revision": source["source_revision"],
                },
                "member_index": artifact_content(collection["member_index"]),
                "expected_member_count": collection["expected_member_count"],
                "watershed_keys": sorted(collection["watershed_keys"]),
            }
        )
    collections.sort(key=lambda collection: collection["collection_key"])

    removals = [
        {
            "watershed_key": removal["watershed_key"],
            "reason": removal["reason"],
            "aliases": sorted(removal["aliases"]),
        }
        for removal in document["expected_removals"]
    ]
    removals.sort(key=lambda removal: removal["watershed_key"])

    lineage = [
        {
            "event_key": event["event_key"],
            "kind": event["kind"],
            "predecessors": sorted(event["predecessors"]),
            "successors": sorted(event["successors"]),
            "reviewed": event["reviewed"],
        }
        for event in document["lineage"]
    ]
    lineage.sort(key=lambda event: event["event_key"])

    return {
        "fingerprint_version": FINGERPRINT_VERSION,
        "subject": "release",
        "compatibility": {
            "schema_version": compatibility["schema_version"],
            "data_contract": compatibility["data_contract"],
            "identity_contract": compatibility["identity_contract"],
            "artifact_contract": compatibility["artifact_contract"],
            "supported_migrations": compatibility["supported_migrations"],
            "materializer": compatibility["materializer"],
            "toolchain": compatibility["toolchain"],
        },
        "collections": collections,
        "expected_removals": removals,
        "lineage": lineage,
    }


NORMALIZERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "artifact": normalize_artifact,
    "run": normalize_run,
    "capability": normalize_capability,
    "watershed-domain": normalize_domain,
    "release": normalize_release,
}


def normalize_document(subject: str, document: dict[str, Any]) -> dict[str, Any]:
    try:
        normalizer = NORMALIZERS[subject]
    except KeyError as error:
        raise FingerprintError(f"unknown fingerprint subject: {subject}") from error
    return normalizer(document)


def fingerprint_document(subject: str, document: dict[str, Any]) -> str:
    return canonical_sha256(normalize_document(subject, document))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute a DB09 semantic fingerprint.")
    parser.add_argument("subject", choices=sorted(NORMALIZERS))
    parser.add_argument("document", type=Path)
    parser.add_argument("--canonical-output", type=Path)
    args = parser.parse_args()

    document = load_json(args.document)
    normalized = normalize_document(args.subject, document)
    if args.canonical_output is not None:
        args.canonical_output.write_bytes(canonical_bytes(normalized))
    print(canonical_sha256(normalized))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
