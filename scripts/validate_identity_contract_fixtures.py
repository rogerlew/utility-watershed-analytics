#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXPECTED_FIELDS = (
    "pws_id",
    "srcname",
    "pws_name",
    "county_nam",
    "state",
    "huc10_id",
    "huc10_name",
    "wws_code",
    "srctype",
    "shape_leng",
    "shape_area",
    "area_km2",
    "owner_type",
    "pop_group",
    "treat_type",
    "conn_group",
    "huc10_pws_names",
    "huc10_owner_types",
    "huc10_pop_groups",
    "huc10_treat_types",
    "huc10_utility_count",
    "runid",
    "geom",
    "simplified_geom",
)
EXPECTED_COLLECTIONS = {"gate-creek", "mill-creek", "nasa-roses", "victoria-ca"}
ALLOWED_AUTHORITIES = {
    "boundary:required",
    "derived:required",
    "explicit_null:required",
    "manifest:required",
    "member_index:required",
    "metadata:nullable",
}
REQUIRED_SCENARIOS = {
    "retained",
    "renamed",
    "replaced",
    "moved",
    "split",
    "merged",
    "metadata_only",
    "geometry_only",
    "removed",
    "unresolved",
}
ALLOWED_CONFLICT_CODES = {
    "ambiguous-identity",
    "metadata-authority-conflict",
    "tombstoned-key-reuse",
}
STATE_KEYS = {
    "aliases",
    "child_fingerprint",
    "collection_keys",
    "display_names",
    "geometry_fingerprint",
    "metadata_fingerprint",
    "runids",
    "tombstones",
    "watershed_keys",
}


class ContractError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def validate_key(value: str, label: str) -> None:
    require(isinstance(value, str), f"{label} must be a string")
    require(1 <= len(value) <= 96, f"{label} must contain 1-96 characters")
    require(KEY_PATTERN.fullmatch(value) is not None, f"{label} has invalid syntax")


def validate_state(state: dict[str, Any], label: str) -> None:
    require(isinstance(state, dict), f"{label} must be an object")
    require(set(state) == STATE_KEYS, f"{label} has unexpected or missing keys")
    for key in ("watershed_keys", "collection_keys", "runids", "display_names", "aliases", "tombstones"):
        require(isinstance(state[key], list), f"{label}.{key} must be an array")
        require(len(state[key]) == len(set(state[key])), f"{label}.{key} contains duplicates")
    for key in state["watershed_keys"] + state["collection_keys"] + state["tombstones"]:
        validate_key(key, f"{label} key")
    for key in ("metadata_fingerprint", "geometry_fingerprint", "child_fingerprint"):
        require(isinstance(state[key], str) and state[key], f"{label}.{key} must be non-empty")


def same_identity(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return (
        before["watershed_keys"] == after["watershed_keys"]
        and before["collection_keys"] == after["collection_keys"]
        and before["runids"] == after["runids"]
    )


def evaluate_scenario(scenario: dict[str, Any]) -> tuple[str, str]:
    scenario_id = scenario["id"]
    kind = scenario["kind"]
    before = scenario["before"]
    after = scenario["after"]
    reviewed_mapping = scenario["reviewed_mapping"]
    conflict_code = scenario["conflict_code"]

    validate_state(before, f"{scenario_id}.before")
    validate_state(after, f"{scenario_id}.after")
    require(isinstance(reviewed_mapping, bool), f"{scenario_id}.reviewed_mapping must be boolean")
    require(
        conflict_code is None or conflict_code in ALLOWED_CONFLICT_CODES,
        f"{scenario_id} has invalid conflict code",
    )

    if kind == "unresolved":
        require(conflict_code in ALLOWED_CONFLICT_CODES, f"{scenario_id} needs a conflict code")
        if conflict_code == "ambiguous-identity":
            require(not reviewed_mapping, f"{scenario_id} ambiguity is already reviewed")
            require(before["runids"] != after["runids"], f"{scenario_id} ambiguity needs differing source revisions")
        elif conflict_code == "metadata-authority-conflict":
            require(same_identity(before, after), f"{scenario_id} metadata conflict changed identity")
            require(
                before["metadata_fingerprint"] != after["metadata_fingerprint"],
                f"{scenario_id} metadata conflict needs differing metadata",
            )
        elif conflict_code == "tombstoned-key-reuse":
            require(
                not set(after["watershed_keys"]).isdisjoint(before["tombstones"]),
                f"{scenario_id} does not reuse a tombstoned key",
            )
        return "reject", conflict_code

    require(conflict_code is None, f"{scenario_id} accepted scenario cannot have a conflict code")

    if kind == "retained":
        require(before == after, f"{scenario_id} retained state must be exact")
    elif kind == "renamed":
        require(same_identity(before, after), f"{scenario_id} rename changed identity")
        require(before["display_names"] != after["display_names"], f"{scenario_id} rename did not change display name")
        require(
            before["metadata_fingerprint"] != after["metadata_fingerprint"],
            f"{scenario_id} rename did not change metadata",
        )
        require(
            before["geometry_fingerprint"] == after["geometry_fingerprint"],
            f"{scenario_id} rename changed geometry",
        )
        require(before["child_fingerprint"] == after["child_fingerprint"], f"{scenario_id} rename changed children")
    elif kind == "replaced":
        require(
            before["watershed_keys"] == after["watershed_keys"],
            f"{scenario_id} replacement changed watershed key",
        )
        require(before["collection_keys"] == after["collection_keys"], f"{scenario_id} replacement changed collection")
        require(before["runids"] != after["runids"], f"{scenario_id} replacement retained run ID")
        require(set(before["runids"]).issubset(after["aliases"]), f"{scenario_id} replacement lost old run alias")
        require(reviewed_mapping, f"{scenario_id} replacement lacks reviewed mapping")
    elif kind == "moved":
        require(before["watershed_keys"] == after["watershed_keys"], f"{scenario_id} move changed watershed key")
        require(before["collection_keys"] != after["collection_keys"], f"{scenario_id} move retained collection")
        require(reviewed_mapping, f"{scenario_id} move lacks reviewed mapping")
    elif kind == "split":
        require(len(before["watershed_keys"]) == 1, f"{scenario_id} split needs one predecessor")
        require(len(after["watershed_keys"]) >= 2, f"{scenario_id} split needs multiple successors")
        require(
            set(before["watershed_keys"]).isdisjoint(after["watershed_keys"]),
            f"{scenario_id} split reused predecessor key",
        )
        require(
            set(before["watershed_keys"]).issubset(after["tombstones"]),
            f"{scenario_id} split did not tombstone predecessor",
        )
        require(reviewed_mapping, f"{scenario_id} split lacks reviewed mapping")
    elif kind == "merged":
        require(len(before["watershed_keys"]) >= 2, f"{scenario_id} merge needs multiple predecessors")
        require(len(after["watershed_keys"]) == 1, f"{scenario_id} merge needs one successor")
        require(
            set(before["watershed_keys"]).isdisjoint(after["watershed_keys"]),
            f"{scenario_id} merge reused predecessor key",
        )
        require(
            set(before["watershed_keys"]).issubset(after["tombstones"]),
            f"{scenario_id} merge did not tombstone predecessors",
        )
        require(reviewed_mapping, f"{scenario_id} merge lacks reviewed mapping")
    elif kind == "metadata_only":
        require(same_identity(before, after), f"{scenario_id} metadata-only changed identity")
        require(
            before["metadata_fingerprint"] != after["metadata_fingerprint"],
            f"{scenario_id} metadata-only did not change metadata",
        )
        require(
            before["geometry_fingerprint"] == after["geometry_fingerprint"],
            f"{scenario_id} metadata-only changed geometry",
        )
        require(
            before["child_fingerprint"] == after["child_fingerprint"],
            f"{scenario_id} metadata-only changed children",
        )
    elif kind == "geometry_only":
        require(same_identity(before, after), f"{scenario_id} geometry-only changed identity")
        require(
            before["geometry_fingerprint"] != after["geometry_fingerprint"],
            f"{scenario_id} geometry-only did not change geometry",
        )
        require(
            before["metadata_fingerprint"] == after["metadata_fingerprint"],
            f"{scenario_id} geometry-only changed metadata",
        )
        require(
            before["child_fingerprint"] == after["child_fingerprint"],
            f"{scenario_id} geometry-only changed children",
        )
    elif kind == "removed":
        require(len(before["watershed_keys"]) >= 1, f"{scenario_id} removal needs a predecessor")
        require(after["watershed_keys"] == [], f"{scenario_id} removal retained a watershed")
        require(
            set(before["watershed_keys"]).issubset(after["tombstones"]),
            f"{scenario_id} removal did not tombstone keys",
        )
        require(reviewed_mapping, f"{scenario_id} removal lacks review")
    else:
        raise ContractError(f"{scenario_id} has unknown scenario kind: {kind}")

    return "accept", kind


def validate_contract(document: dict[str, Any]) -> dict[str, int]:
    require(set(document) == {"contract_version", "collections", "scenarios"}, "fixture has unexpected top-level keys")
    require(document["contract_version"] == 1, "contract_version must be 1")
    collections = document["collections"]
    scenarios = document["scenarios"]
    require(isinstance(collections, list), "collections must be an array")
    require(isinstance(scenarios, list), "scenarios must be an array")

    collection_keys = []
    watershed_keys = []
    for collection in collections:
        require(
            set(collection)
            == {
                "collection_key",
                "kind",
                "source_revisions",
                "sample_watershed_keys",
                "field_authority",
            },
            "collection has unexpected keys",
        )
        collection_key = collection["collection_key"]
        validate_key(collection_key, "collection_key")
        collection_keys.append(collection_key)
        require(collection["kind"] in {"batch", "standalone"}, f"{collection_key} has invalid kind")
        require(
            isinstance(collection["source_revisions"], list)
            and collection["source_revisions"],
            f"{collection_key} needs source revisions",
        )
        require(
            isinstance(collection["sample_watershed_keys"], list)
            and collection["sample_watershed_keys"],
            f"{collection_key} needs sample keys",
        )
        for watershed_key in collection["sample_watershed_keys"]:
            validate_key(watershed_key, f"{collection_key} watershed_key")
            watershed_keys.append(watershed_key)
        authority = collection["field_authority"]
        require(set(authority) == set(EXPECTED_FIELDS), f"{collection_key} field coverage mismatch")
        require(set(authority.values()).issubset(ALLOWED_AUTHORITIES), f"{collection_key} has invalid authority")

    require(set(collection_keys) == EXPECTED_COLLECTIONS, "current collection coverage mismatch")
    require(len(collection_keys) == len(set(collection_keys)), "duplicate collection_key")
    require(len(watershed_keys) == len(set(watershed_keys)), "duplicate sample watershed_key")

    scenario_ids = []
    scenario_kinds = set()
    accepted = 0
    rejected = 0
    for scenario in scenarios:
        require(
            set(scenario)
            == {
                "id",
                "kind",
                "before",
                "after",
                "reviewed_mapping",
                "conflict_code",
                "expected",
            },
            "scenario has unexpected keys",
        )
        scenario_id = scenario["id"]
        validate_key(scenario_id, "scenario id")
        scenario_ids.append(scenario_id)
        scenario_kinds.add(scenario["kind"])
        expected = scenario["expected"]
        require(set(expected) == {"decision", "code"}, f"{scenario_id}.expected has unexpected keys")
        actual = evaluate_scenario(scenario)
        require(
            actual == (expected["decision"], expected["code"]),
            f"{scenario_id} expected {expected} but got {actual}",
        )
        if actual[0] == "accept":
            accepted += 1
        else:
            rejected += 1

    require(len(scenario_ids) == len(set(scenario_ids)), "duplicate scenario id")
    require(REQUIRED_SCENARIOS.issubset(scenario_kinds), "scenario coverage mismatch")
    require(rejected >= len(ALLOWED_CONFLICT_CODES), "each conflict class needs a rejected fixture")
    return {
        "accepted_scenarios": accepted,
        "collections": len(collections),
        "fields_per_collection": len(EXPECTED_FIELDS),
        "rejected_scenarios": rejected,
        "scenarios": len(scenarios),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate DB07 identity contract fixtures")
    parser.add_argument("fixture", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    document = json.loads(arguments.fixture.read_text(encoding="utf-8"))
    summary = validate_contract(document)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
