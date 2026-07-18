#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIRECTORY = ROOT / "data-releases" / "storage-contract" / "v1"
EXPECTED_CLASSES = {
    "release-control",
    "watershed-vector",
    "thematic-tabular",
    "rhessys-input",
    "rhessys-output",
    "validation-evidence",
}
EXPECTED_FAILURES = {
    "partial-copy",
    "hash-collision",
    "corrupt-backup",
    "accidental-deletion",
    "restore-active-two-rollbacks",
    "storage-full",
    "forest1-unavailable",
}
SHA_KEY_REGEX = r"^objects/sha256/[a-f0-9]{2}/[a-f0-9]{64}$"
EXPECTED_ROOT = "/wc1/utility-watershed-analytics-artifacts/v1"


class ContractError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_unique(values: list[str], label: str) -> None:
    require(len(values) == len(set(values)), f"{label} contains duplicates")


def validate_policy(policy: dict[str, Any]) -> None:
    require(policy["contract_version"] == 1, "artifact-store contract version must be 1")

    storage = policy["storage"]
    require(storage["id"] == "forest1-local-filesystem", "storage must remain on forest1")
    require(storage["host"] == "forest1", "storage host must be forest1")
    require(storage["root"] == EXPECTED_ROOT, "artifact backup root differs")
    require(
        storage["database_backup_root"] == "/wc1/utility-watershed-analytics-db-backups",
        "database backup root differs",
    )
    require(not storage["network_service_required"], "network service is not required")
    require(not storage["paid_provider_required"], "paid provider is prohibited")

    ownership = policy["ownership"]
    require(ownership["operator"] == "roger", "operator ownership differs")
    require(ownership["single_operator"], "single-operator contract differs")
    require(ownership["directory_mode"] == "0700", "directory mode must be 0700")
    require(ownership["file_mode"] == "0600", "file mode must be 0600")
    require(ownership["public_access_prohibited"], "public filesystem access is prohibited")
    require(not ownership["credentials_required"], "local artifact backup needs no credentials")

    environments = [namespace["environment"] for namespace in policy["namespaces"]]
    require(environments == ["test", "production"], "exact test and production namespaces required")
    for namespace in policy["namespaces"]:
        require(
            namespace["path"] == f"{EXPECTED_ROOT}/{namespace['environment']}",
            f"{namespace['environment']} namespace path differs",
        )

    key_layout = policy["key_layout"]
    require(key_layout["algorithm"] == "sha256", "key layout must use SHA-256")
    require(key_layout["regex"] == SHA_KEY_REGEX, "content-addressed key regex differs")
    re.compile(key_layout["regex"])
    require(not key_layout["mutable_alias_is_authority"], "mutable aliases cannot be authority")
    require(not key_layout["overwrite_allowed"], "content-addressed overwrite must be prohibited")

    publication = policy["publication"]
    for field in (
        "write_to_unique_temporary_file",
        "atomic_promote_after_verification",
        "verify_sha256_before_copy",
        "verify_sha256_after_copy",
        "existing_key_requires_full_verification",
        "partial_file_cleanup_required",
    ):
        require(publication[field], f"publication control {field} is required")

    retention = policy["retention"]
    require(retention["minimum_releases"] >= 3, "active plus two rollback releases are required")
    require(
        retention["required_release_roles"] == ["active", "rollback-1", "rollback-2"],
        "retained release roles differ",
    )
    require(retention["retained_release_ttl"] is None, "retained releases cannot have TTL")
    require(not retention["automatic_deletion_allowed"], "automatic deletion is prohibited")
    require(retention["manual_preview_required"], "manual deletion preview is required")

    recovery = policy["recovery"]
    require(recovery["restore_host"] == "forest1", "restore host must be forest1")
    require(recovery["minimum_backed_up_releases"] >= 3, "backup must include active plus two")
    require(recovery["verify_after_backup"], "post-backup verification is required")
    require(recovery["verify_after_restore"], "post-restore verification is required")
    require(recovery["quarterly_restore_drill_required"], "quarterly restore drill is required")
    require(not recovery["provider_dependency"], "provider dependency is prohibited")

    monitoring = policy["monitoring"]
    require(monitoring["minimum_free_bytes"] >= 100 * 1024**3, "free-space floor is below 100 GiB")
    require(monitoring["check_free_space_before_copy"], "free-space preflight is required")
    require(monitoring["inventory_hash_required"], "inventory hash is required")
    require(monitoring["nonzero_exit_on_failure"], "failures must exit nonzero")
    require(not monitoring["external_alerting_required"], "external alerting is outside this contract")


def validate_artifact_classes(document: dict[str, Any]) -> None:
    require(document["contract_version"] == 1, "artifact-class contract version must be 1")
    classes = document["classes"]
    keys = [item["class_key"] for item in classes]
    require_unique(keys, "artifact class keys")
    require(set(keys) == EXPECTED_CLASSES, "artifact class coverage differs")
    members = []
    for item in classes:
        require(item["members"], f"{item['class_key']} has no members")
        members.extend(item["members"])
        require("required" in item["license_policy"], f"{item['class_key']} lacks license requirement")
        require(item["sensitivity"] in {"public", "public-sanitized"}, "sensitivity must remain public")
        require(item["pii"] == "prohibited", f"{item['class_key']} must prohibit PII")
        require("active-plus-two-rollbacks" in item["retention"], f"{item['class_key']} retention differs")
    require_unique(members, "artifact class members")


def validate_threat_review(document: dict[str, Any]) -> None:
    require(document["contract_version"] == 1, "threat-review contract version must be 1")
    cases = document["cases"]
    keys = [item["case_key"] for item in cases]
    require_unique(keys, "artifact backup failure keys")
    require(set(keys) == EXPECTED_FAILURES, "threat/failure coverage differs")
    for item in cases:
        for field in ("prevention", "detection", "response", "owner", "db10a_proof"):
            require(isinstance(item[field], str) and item[field], f"{item['case_key']} lacks {field}")
        require(item["owner"] == "operator", f"{item['case_key']} owner differs")


def validate_suite(contract_directory: Path = CONTRACT_DIRECTORY) -> dict[str, int]:
    policy = load_json(contract_directory / "artifact-store-policy.json")
    classes = load_json(contract_directory / "artifact-classes.json")
    threats = load_json(contract_directory / "threat-review.json")
    validate_policy(policy)
    validate_artifact_classes(classes)
    validate_threat_review(threats)
    return {
        "namespaces": len(policy["namespaces"]),
        "operators": 1,
        "artifact_classes": len(classes["classes"]),
        "failure_cases": len(threats["cases"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the DB10 artifact backup contract.")
    parser.add_argument("--contract-directory", type=Path, default=CONTRACT_DIRECTORY)
    args = parser.parse_args()
    try:
        summary = validate_suite(args.contract_directory)
    except (ContractError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps({"status": "passed", **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
