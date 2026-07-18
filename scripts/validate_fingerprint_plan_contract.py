#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from release_fingerprints import canonical_sha256, fingerprint_document, load_json


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIRECTORY = ROOT / "data-releases" / "fixtures" / "v1" / "fingerprint-plans"
PLAN_SCHEMA_DIRECTORY = ROOT / "data-releases" / "schema" / "v1" / "plans"
EXPECTED_PLAN_SCHEMAS = {
    "deployment-plan.schema.json",
    "empty-build-plan.schema.json",
    "exact-inverse-plan.schema.json",
    "forward-plan.schema.json",
}
SUBJECT_PATHS = {
    "artifact": ROOT / "data-releases" / "fixtures" / "v1" / "valid" / "artifact-reference.json",
    "run": FIXTURE_DIRECTORY / "run.json",
    "capability": ROOT / "data-releases" / "fixtures" / "v1" / "valid" / "rhessys-capability-index.json",
    "watershed-domain": FIXTURE_DIRECTORY / "watershed-domain.json",
    "release": ROOT / "data-releases" / "fixtures" / "v1" / "valid" / "release-manifest.json",
}
PLAN_PATHS = {
    "forward": FIXTURE_DIRECTORY / "plans" / "forward.json",
    "exact-inverse": FIXTURE_DIRECTORY / "plans" / "exact-inverse.json",
    "empty-build": FIXTURE_DIRECTORY / "plans" / "empty-build.json",
}
PLAN_SCHEMAS = {
    "forward": "forward-plan.schema.json",
    "exact-inverse": "exact-inverse-plan.schema.json",
    "empty-build": "empty-build-plan.schema.json",
}
CHANNEL_ORDER = {
    "identity": 0,
    "metadata": 1,
    "geometry": 2,
    "children": 3,
    "capability": 4,
}
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
REQUIRED_ARTIFACT_ROLES = {
    "metadata",
    "boundary",
    "subcatchments",
    "channels",
    "hillslopes",
    "soils",
    "landuse",
}
RUN_FIELDS = {
    "collection_key",
    "watershed_key",
    "runid",
    "display_name",
    "aliases",
    "artifact_fingerprints",
    "transformation_lineage_fingerprint",
    "rhessys_index_fingerprint",
    "expected",
    "capability_fingerprint",
}
DOMAIN_RUN_FIELDS = {
    "collection_key",
    "watershed_key",
    "runid",
    "run_fingerprint",
    "capability_fingerprint",
}


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ContractError(code, message)


def require_sha256(value: Any, label: str, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    require(
        isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None,
        "fingerprint-shape",
        f"{label} must be a lowercase SHA-256",
    )


def validate_subject_shapes(documents: dict[str, dict[str, Any]]) -> None:
    run = documents["run"]
    require(set(run) == RUN_FIELDS, "run-shape", "run fingerprint input fields differ")
    require(len(run["aliases"]) == len(set(run["aliases"])), "run-alias", "run aliases contain duplicates")
    require(
        set(run["artifact_fingerprints"]) == REQUIRED_ARTIFACT_ROLES,
        "run-artifact-roles",
        "run artifact fingerprint roles differ",
    )
    for role, value in run["artifact_fingerprints"].items():
        require_sha256(value, f"run artifact {role}")
    require_sha256(run["transformation_lineage_fingerprint"], "transformation fingerprint", nullable=True)
    require_sha256(run["rhessys_index_fingerprint"], "RHESSys index fingerprint", nullable=True)
    require_sha256(run["capability_fingerprint"], "capability fingerprint", nullable=True)

    domain = documents["watershed-domain"]
    require(set(domain) == {"runs"}, "domain-shape", "domain fingerprint input fields differ")
    identities = []
    for run_state in domain["runs"]:
        require(set(run_state) == DOMAIN_RUN_FIELDS, "domain-run-shape", "domain run fields differ")
        identity = (
            run_state["collection_key"],
            run_state["watershed_key"],
            run_state["runid"],
        )
        identities.append(identity)
        require_sha256(run_state["run_fingerprint"], "domain run fingerprint")
        require_sha256(run_state["capability_fingerprint"], "domain capability fingerprint", nullable=True)
    require(len(identities) == len(set(identities)), "domain-identity", "domain run identity contains duplicates")

    capability_fingerprint = fingerprint_document("capability", documents["capability"])
    require(
        run["capability_fingerprint"] == capability_fingerprint,
        "run-capability-link",
        "run capability fingerprint does not match capability subject",
    )
    run_fingerprint = fingerprint_document("run", run)
    matching_domain_runs = [
        state
        for state in domain["runs"]
        if state["collection_key"] == run["collection_key"]
        and state["watershed_key"] == run["watershed_key"]
        and state["runid"] == run["runid"]
    ]
    require(len(matching_domain_runs) == 1, "domain-run-link", "domain lacks the composed run subject")
    require(
        matching_domain_runs[0]["run_fingerprint"] == run_fingerprint
        and matching_domain_runs[0]["capability_fingerprint"] == capability_fingerprint,
        "domain-fingerprint-link",
        "domain fingerprints do not match composed run and capability subjects",
    )


def build_plan_validators(
    schema_directory: Path = PLAN_SCHEMA_DIRECTORY,
) -> dict[str, Draft202012Validator]:
    paths = sorted(schema_directory.glob("*.schema.json"))
    names = {path.name for path in paths}
    require(
        names == EXPECTED_PLAN_SCHEMAS,
        "plan-schema-coverage",
        f"plan schema coverage mismatch: {sorted(names)}",
    )
    schemas = {path.name: load_json(path) for path in paths}
    registry = Registry()
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        require("$id" in schema, "plan-schema-id", f"{name} lacks $id")
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return {
        name: Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
        for name, schema in schemas.items()
    }


def sum_deltas(actions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        field: sum(action["row_delta"][field] for action in actions)
        for field in ("watersheds", "subcatchments", "channels")
    }


def validate_plan_semantics(plan: dict[str, Any]) -> None:
    actions = plan["actions"]
    keys = [action["watershed_key"] for action in actions]
    require(keys == sorted(keys), "action-order", "plan actions are not sorted by watershed_key")
    require(len(keys) == len(set(keys)), "action-identity", "plan watershed actions contain duplicates")
    require(
        plan["expected_row_delta"] == sum_deltas(actions),
        "row-delta-total",
        "expected row delta does not equal action totals",
    )
    require(plan["base"] != plan["target"], "same-state-plan", "plan base and target are identical")

    for action in actions:
        channels = action["change_channels"]
        require(
            channels == sorted(channels, key=CHANNEL_ORDER.__getitem__),
            "channel-order",
            f"{action['watershed_key']} change channels are not canonical",
        )
        if action["operation"] == "retain":
            require(action["before"] == action["after"], "retain-state", "retained action changed run state")
            require(
                action["row_delta"] == {"watersheds": 0, "subcatchments": 0, "channels": 0},
                "retain-delta",
                "retained action changed row counts",
            )
        elif action["operation"] == "change":
            require(action["before"] != action["after"], "change-state", "changed action retained exact run state")


def assert_plan_base(plan: dict[str, Any], observed_base: dict[str, Any]) -> None:
    require(
        plan["base"] == observed_base,
        "base-mismatch",
        "observed base does not exactly match reviewed plan base",
    )


def inverse_operation(operation: str) -> str:
    return {"add": "remove", "remove": "add", "change": "change", "retain": "retain"}[operation]


def validate_exact_inverse(forward: dict[str, Any], inverse: dict[str, Any]) -> None:
    require(inverse["base"] == forward["target"], "inverse-base", "inverse base is not forward target")
    require(inverse["target"] == forward["base"], "inverse-target", "inverse target is not forward base")
    for field in (
        "fingerprint_version",
        "data_contract",
        "identity_contract",
        "supported_migration",
        "materializer",
    ):
        require(inverse[field] == forward[field], "inverse-coordinate", f"inverse {field} differs from forward")
    require(
        inverse["inverse_of_plan_sha256"] == canonical_sha256(forward),
        "inverse-plan-hash",
        "inverse does not reference the canonical forward plan hash",
    )
    require(len(inverse["actions"]) == len(forward["actions"]), "inverse-action-count", "inverse action count differs")
    for forward_action, inverse_action in zip(forward["actions"], inverse["actions"], strict=True):
        require(
            inverse_action["watershed_key"] == forward_action["watershed_key"],
            "inverse-action-key",
            "inverse action key differs",
        )
        require(
            inverse_action["operation"] == inverse_operation(forward_action["operation"]),
            "inverse-operation",
            f"{forward_action['watershed_key']} operation is not mirrored",
        )
        require(inverse_action["before"] == forward_action["after"], "inverse-before", "inverse before state differs")
        require(inverse_action["after"] == forward_action["before"], "inverse-after", "inverse after state differs")
        require(
            inverse_action["change_channels"] == forward_action["change_channels"],
            "inverse-channels",
            "inverse change channels differ",
        )
        require(
            all(
                inverse_action["row_delta"][field] == -forward_action["row_delta"][field]
                for field in ("watersheds", "subcatchments", "channels")
            ),
            "inverse-delta",
            "inverse row delta is not negated",
        )


def validate_empty_build(plan: dict[str, Any]) -> None:
    require(plan["base"] == {"kind": "EMPTY"}, "empty-base", "empty-build base is not EMPTY")
    require(plan["actions"], "empty-actions", "empty-build plan has no actions")
    require(
        all(action["operation"] == "add" for action in plan["actions"]),
        "empty-operation",
        "empty-build plan contains a non-add action",
    )


def reordered_documents(documents: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    reordered = copy.deepcopy(documents)
    reordered["artifact"]["uri"] = "https://mirror.example.test/identical/artifact.json"
    reordered["run"]["aliases"].reverse()
    reordered["capability"]["spatial_inputs"].reverse()
    reordered["capability"]["parquets"].reverse()
    reordered["capability"]["geotiffs"].reverse()
    for parquet in reordered["capability"]["parquets"]:
        parquet["variables"].reverse()
        parquet["artifact"]["uri"] = "https://mirror.example.test/identical/basin.parquet"
    reordered["watershed-domain"]["runs"].reverse()
    reordered["release"]["collections"].reverse()
    for collection in reordered["release"]["collections"]:
        collection["watershed_keys"].reverse()
    reordered["release"]["expected_removals"].reverse()
    reordered["release"]["lineage"].reverse()
    reordered["release"]["release_id"] = "2026-07-17.99"
    reordered["release"]["created_at"] = "2026-07-17T23:59:59Z"
    reordered["release"]["validation_report"]["uri"] = (
        "https://mirror.example.test/identical/validation.json"
    )
    reordered["release"]["collections"][0]["source"]["authentication"][
        "secret_ref"
    ] = "DIFFERENT_EXAMPLE_TOKEN_REFERENCE"
    return reordered


def semantically_changed_documents(
    documents: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    changed = copy.deepcopy(documents)
    changed["artifact"]["bytes"] += 1
    changed["run"]["display_name"] = "Changed Example North"
    changed["capability"]["durable_base_uri"] = "https://artifacts.example.test/rhessys/example-north-v2/"
    changed["watershed-domain"]["runs"][0]["run_fingerprint"] = "f" * 64
    changed["release"]["collections"][0]["display_name"] = "Changed Collection"
    return changed


def validate_suite(
    fixture_directory: Path = FIXTURE_DIRECTORY,
    schema_directory: Path = PLAN_SCHEMA_DIRECTORY,
) -> dict[str, int]:
    subject_paths = SUBJECT_PATHS
    plan_paths = PLAN_PATHS
    if fixture_directory != FIXTURE_DIRECTORY:
        subject_paths = {
            "artifact": fixture_directory / "artifact-reference.json",
            "run": fixture_directory / "run.json",
            "capability": fixture_directory / "rhessys-capability-index.json",
            "watershed-domain": fixture_directory / "watershed-domain.json",
            "release": fixture_directory / "release-manifest.json",
        }
        plan_paths = {
            "forward": fixture_directory / "plans" / "forward.json",
            "exact-inverse": fixture_directory / "plans" / "exact-inverse.json",
            "empty-build": fixture_directory / "plans" / "empty-build.json",
        }

    documents = {subject: load_json(path) for subject, path in subject_paths.items()}
    validate_subject_shapes(documents)
    golden = load_json(fixture_directory / "golden-fingerprints.json")
    require(golden["fingerprint_version"] == 1, "golden-version", "golden fingerprint version differs")

    actual = {
        subject: fingerprint_document(subject, document)
        for subject, document in documents.items()
    }
    require(actual == {key: golden[key] for key in actual}, "golden-mismatch", "golden fingerprints differ")

    reordered = reordered_documents(documents)
    for subject, document in reordered.items():
        require(
            fingerprint_document(subject, document) == actual[subject],
            "order-invariance",
            f"{subject} fingerprint changed with set ordering",
        )
    changed = semantically_changed_documents(documents)
    for subject, document in changed.items():
        require(
            fingerprint_document(subject, document) != actual[subject],
            "semantic-sensitivity",
            f"{subject} fingerprint ignored a semantic change",
        )

    validators = build_plan_validators(schema_directory)
    plans = {kind: load_json(path) for kind, path in plan_paths.items()}
    for kind, plan in plans.items():
        errors = list(validators[PLAN_SCHEMAS[kind]].iter_errors(plan))
        require(
            not errors,
            "plan-structural",
            f"{kind} plan failed schema: {errors[0].message if errors else ''}",
        )
        validate_plan_semantics(plan)
    validate_exact_inverse(plans["forward"], plans["exact-inverse"])
    validate_empty_build(plans["empty-build"])
    assert_plan_base(plans["forward"], load_json(fixture_directory / "observed-base.json"))
    try:
        assert_plan_base(plans["forward"], load_json(fixture_directory / "wrong-base.json"))
    except ContractError as error:
        require(error.code == "base-mismatch", "wrong-base-code", "wrong base failed unexpectedly")
    else:
        raise ContractError("wrong-base-passed", "wrong observed base unexpectedly passed")

    return {
        "fingerprint_subjects": len(actual),
        "plan_schemas": len(validators),
        "plans": len(plans),
        "semantic_mutations": len(changed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DB09 fingerprints and plans.")
    parser.add_argument("--fixture-directory", type=Path, default=FIXTURE_DIRECTORY)
    parser.add_argument("--schema-directory", type=Path, default=PLAN_SCHEMA_DIRECTORY)
    args = parser.parse_args()
    try:
        summary = validate_suite(args.fixture_directory, args.schema_directory)
    except (ContractError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps({"status": "passed", **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
