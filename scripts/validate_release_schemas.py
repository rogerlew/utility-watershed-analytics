#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIRECTORY = ROOT / "data-releases" / "schema" / "v1"
FIXTURE_DIRECTORY = ROOT / "data-releases" / "fixtures" / "v1"
CASE_FILE = FIXTURE_DIRECTORY / "cases.json"
EXPECTED_SCHEMAS = {
    "artifact-reference.schema.json",
    "batch-member-index.schema.json",
    "compatibility-envelope.schema.json",
    "release-manifest.schema.json",
    "rhessys-capability-index.schema.json",
    "transformation-lineage.schema.json",
    "validation-report.schema.json",
}
EXPECTED_NEGATIVE_CODES = {
    "additionalProperties",
    "const",
    "duplicate-collection-key",
    "duplicate-watershed-key",
    "minItems",
    "pattern",
    "required",
    "target-overlapping-removal",
}
PROHIBITED_SECRET_KEYS = {
    "credential",
    "credentials",
    "passwd",
    "password",
    "secret",
    "token",
}


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ContractError(code, message)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validation_error_codes(error: ValidationError) -> set[str]:
    codes = {str(error.validator)}
    for nested_error in error.context:
        codes.update(validation_error_codes(nested_error))
    return codes


def build_validators(schema_directory: Path = SCHEMA_DIRECTORY) -> dict[str, Draft202012Validator]:
    schema_paths = sorted(schema_directory.glob("*.schema.json"))
    schema_names = {path.name for path in schema_paths}
    require(
        schema_names == EXPECTED_SCHEMAS,
        "schema-coverage",
        f"schema coverage mismatch: expected {sorted(EXPECTED_SCHEMAS)}, found {sorted(schema_names)}",
    )

    schemas = {path.name: load_json(path) for path in schema_paths}
    registry = Registry()
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        require("$id" in schema, "schema-id", f"{name} is missing $id")
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))

    return {
        name: Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
        for name, schema in schemas.items()
    }


def require_unique(values: Iterable[str], code: str, label: str) -> None:
    materialized = list(values)
    require(len(materialized) == len(set(materialized)), code, f"{label} contains duplicates")


def validate_safe_content(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            lowered = key.lower()
            require(
                lowered == "secret_ref" or lowered not in PROHIBITED_SECRET_KEYS,
                "prohibited-secret-key",
                f"{path}.{key} is a prohibited credential-bearing key",
            )
            validate_safe_content(nested_value, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            validate_safe_content(nested_value, f"{path}[{index}]")
    elif isinstance(value, str) and value.startswith(("http://", "https://")):
        parsed = urlsplit(value)
        require(parsed.scheme == "https", "unsafe-uri", f"{path} must use HTTPS")
        require(parsed.username is None and parsed.password is None, "unsafe-uri", f"{path} contains URI userinfo")
        require(not parsed.query and not parsed.fragment, "unsafe-uri", f"{path} contains a query or fragment")


def validate_batch_member_index(document: dict[str, Any]) -> None:
    members = document["members"]
    require(
        document["expected_member_count"] == len(members),
        "member-count-mismatch",
        "expected_member_count does not match members",
    )
    require_unique(
        (member["watershed_key"] for member in members),
        "duplicate-watershed-key",
        "member watershed_key",
    )
    require_unique(
        (member["runid"] for member in members),
        "duplicate-runid",
        "member runid",
    )


def validate_release_manifest(document: dict[str, Any]) -> None:
    collections = document["collections"]
    require_unique(
        (collection["collection_key"] for collection in collections),
        "duplicate-collection-key",
        "release collection_key",
    )
    target_keys: list[str] = []
    for collection in collections:
        require(
            collection["expected_member_count"] == len(collection["watershed_keys"]),
            "member-count-mismatch",
            f"{collection['collection_key']} expected_member_count does not match watershed_keys",
        )
        target_keys.extend(collection["watershed_keys"])
    require_unique(target_keys, "duplicate-watershed-key", "release watershed_key")

    removal_keys = [removal["watershed_key"] for removal in document["expected_removals"]]
    require_unique(removal_keys, "duplicate-removal-key", "expected removal watershed_key")
    require(
        set(target_keys).isdisjoint(removal_keys),
        "target-overlapping-removal",
        "an expected removal also appears in the target release",
    )
    require_unique(
        (event["event_key"] for event in document["lineage"]),
        "duplicate-lineage-event",
        "lineage event_key",
    )


def validate_rhessys_capability_index(document: dict[str, Any]) -> None:
    require_unique(
        (item["key"] for item in document["scenarios"]),
        "duplicate-scenario-key",
        "RHESSys scenario key",
    )
    for item in document["scenarios"]:
        require_unique(
            item["variables"],
            "duplicate-scenario-variable",
            f"RHESSys {item['key']} scenario variable",
        )
    require_unique(
        (item["role"] for item in document["spatial_inputs"]),
        "duplicate-spatial-role",
        "RHESSys spatial input role",
    )
    require_unique(
        (item["dataset_key"] for item in document["parquets"]),
        "duplicate-parquet-role",
        "RHESSys parquet dataset key",
    )
    for item in document["parquets"]:
        require_unique(
            (column["name"] for column in item["columns"]),
            "duplicate-parquet-column",
            f"RHESSys {item['role']} parquet column",
        )
        column_names = {column["name"] for column in item["columns"]}
        require(
            {item["spatial_id_field"], "year", *(variable["name"] for variable in item["variables"])}
            <= column_names,
            "missing-parquet-column",
            f"RHESSys {item['role']} parquet lacks a declared identity, year, or variable column",
        )
        require(
            item["year_range"][0] <= item["year_range"][1],
            "invalid-year-range",
            f"RHESSys {item['role']} year_range is reversed",
        )
    if document["mode"] in {"precomputed", "both"}:
        require_unique(
            (f"{item['scenario']}:{item['variable']}" for item in document["geotiffs"]),
            "duplicate-geotiff-pair",
            "RHESSys GeoTIFF scenario and variable pair",
        )
        expected = {
            (scenario["key"], variable)
            for scenario in document["scenarios"]
            for variable in scenario["variables"]
        }
        observed = {(item["scenario"], item["variable"]) for item in document["geotiffs"]}
        require(
            observed == expected,
            "incomplete-scenario-assets",
            "RHESSys GeoTIFF assets do not exactly cover declared scenarios",
        )
    if document["mode"] in {"dynamic", "both"}:
        scenario_keys = {item["key"] for item in document["scenarios"]}
        require(
            all(item["scenario"] in scenario_keys for item in document["parquets"]),
            "missing-dynamic-variable",
            "RHESSys Parquet scenario is undeclared",
        )
        coordinates = [
            (item["scenario"], item["role"], variable["name"])
            for item in document["parquets"]
            for variable in item["variables"]
        ]
        require_unique(
            coordinates,
            "duplicate-parquet-role",
            "RHESSys Parquet query coordinate",
        )
        geometry_coordinates = {
            (geometry["scale"], scenario)
            for geometry in document["geometries"]
            for scenario in geometry["scenarios"]
        }
        require(
            all(
                item["role"] == "basin"
                or (item["role"], item["scenario"]) in geometry_coordinates
                for item in document["parquets"]
            ),
            "missing-dynamic-variable",
            "RHESSys dynamic query geometry is absent",
        )
        expected_variables = {
            variable
            for scenario in document["scenarios"]
            for variable in scenario["variables"]
        }
        parquet_variables = {
            variable["name"]
            for parquet in document["parquets"]
            for variable in parquet["variables"]
        }
        require(
            expected_variables <= parquet_variables,
            "missing-dynamic-variable",
            "RHESSys dynamic scenario variable is absent from Parquet metadata",
        )


def validate_transformation_lineage(document: dict[str, Any]) -> None:
    require_unique(
        (decision["field"] for decision in document["field_decisions"]),
        "duplicate-field-decision",
        "transformation field decision",
    )
    input_hashes = {artifact["sha256"] for artifact in document["inputs"]}
    require(
        document["output"]["sha256"] not in input_hashes,
        "output-reuses-input",
        "transformation output must not reuse an input checksum",
    )


def validate_validation_report(document: dict[str, Any]) -> None:
    checks = document["checks"]
    require_unique((check["code"] for check in checks), "duplicate-check-code", "validation check code")
    failed_checks = [check for check in checks if check["status"] == "failed"]
    require(
        document["status"] == ("failed" if failed_checks else "passed"),
        "report-status-mismatch",
        "validation report status does not match its checks",
    )
    require(
        datetime.fromisoformat(document["started_at"].replace("Z", "+00:00"))
        <= datetime.fromisoformat(document["completed_at"].replace("Z", "+00:00")),
        "report-time-order",
        "validation report completed_at precedes started_at",
    )


SEMANTIC_VALIDATORS = {
    "batch-member-index.schema.json": validate_batch_member_index,
    "release-manifest.schema.json": validate_release_manifest,
    "rhessys-capability-index.schema.json": validate_rhessys_capability_index,
    "transformation-lineage.schema.json": validate_transformation_lineage,
    "validation-report.schema.json": validate_validation_report,
}


def validate_semantics(schema_name: str, document: dict[str, Any]) -> None:
    validate_safe_content(document)
    validator = SEMANTIC_VALIDATORS.get(schema_name)
    if validator is not None:
        validator(document)


def validate_release_index_consistency(valid_documents: dict[str, dict[str, Any]]) -> None:
    manifest = valid_documents["release-manifest.schema.json"]
    index = valid_documents["batch-member-index.schema.json"]
    matching = [
        collection
        for collection in manifest["collections"]
        if collection["collection_key"] == index["collection_key"]
    ]
    require(
        len(matching) == 1,
        "release-index-collection",
        "valid release must reference the valid member index collection",
    )
    collection = matching[0]
    index_keys = [member["watershed_key"] for member in index["members"]]
    require(
        collection["expected_member_count"] == index["expected_member_count"],
        "release-index-count",
        "release and member index expected counts differ",
    )
    require(
        collection["watershed_keys"] == index_keys,
        "release-index-membership",
        "release and member index watershed membership or order differs",
    )


def validate_suite(
    fixture_directory: Path = FIXTURE_DIRECTORY,
    schema_directory: Path = SCHEMA_DIRECTORY,
) -> dict[str, int]:
    validators = build_validators(schema_directory)
    cases = load_json(fixture_directory / "cases.json")
    require(
        set(cases) == {"schema_version", "valid", "invalid"},
        "case-format",
        "cases.json has unexpected keys",
    )
    require(cases["schema_version"] == 1, "case-version", "cases.json schema_version must be 1")

    valid_schema_names = [case["schema"] for case in cases["valid"]]
    require(
        set(valid_schema_names) == EXPECTED_SCHEMAS and len(valid_schema_names) == len(EXPECTED_SCHEMAS),
        "valid-case-coverage",
        "valid cases must cover every schema exactly once",
    )
    negative_codes = {case["code"] for case in cases["invalid"]}
    require(
        negative_codes == EXPECTED_NEGATIVE_CODES,
        "negative-case-coverage",
        f"negative case coverage mismatch: {sorted(negative_codes)}",
    )

    valid_documents: dict[str, dict[str, Any]] = {}
    for case in cases["valid"]:
        schema_name = case["schema"]
        require(schema_name in validators, "unknown-schema", f"unknown schema {schema_name}")
        document = load_json(fixture_directory / case["instance"])
        errors = list(validators[schema_name].iter_errors(document))
        require(
            not errors,
            "valid-structural",
            f"{case['instance']} failed schema validation: "
            f"{errors[0].message if errors else ''}",
        )
        validate_semantics(schema_name, document)
        valid_documents[schema_name] = document

    validate_release_index_consistency(valid_documents)

    for case in cases["invalid"]:
        schema_name = case["schema"]
        require(schema_name in validators, "unknown-schema", f"unknown schema {schema_name}")
        document = load_json(fixture_directory / case["instance"])
        errors = list(validators[schema_name].iter_errors(document))
        if case["phase"] == "structural":
            codes = {code for error in errors for code in validation_error_codes(error)}
            require(
                case["code"] in codes,
                "negative-case-passed",
                f"{case['instance']} did not fail with {case['code']}; "
                f"found {sorted(codes)}",
            )
        elif case["phase"] == "semantic":
            require(
                not errors,
                "negative-case-structural",
                f"{case['instance']} failed structurally before semantic validation",
            )
            try:
                validate_semantics(schema_name, document)
            except ContractError as error:
                require(
                    error.code == case["code"],
                    "negative-case-code",
                    f"{case['instance']} failed with {error.code}, "
                    f"expected {case['code']}",
                )
            else:
                raise ContractError(
                    "negative-case-passed",
                    f"{case['instance']} unexpectedly passed semantic validation",
                )
        else:
            raise ContractError("case-phase", f"{case['instance']} has invalid phase {case['phase']}")

    return {
        "schemas": len(validators),
        "valid_cases": len(cases["valid"]),
        "invalid_cases": len(cases["invalid"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DB08 release schemas and fixtures.")
    parser.add_argument("--fixture-directory", type=Path, default=FIXTURE_DIRECTORY)
    parser.add_argument("--schema-directory", type=Path, default=SCHEMA_DIRECTORY)
    args = parser.parse_args()
    try:
        summary = validate_suite(args.fixture_directory, args.schema_directory)
    except (ContractError, ValidationError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps({"status": "passed", **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
