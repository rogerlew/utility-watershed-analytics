#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIRECTORY = ROOT / "data-releases" / "storage-contract" / "v1"
EXPECTED_ROLES = {
    "publisher",
    "runtime-reader",
    "deployment-reader",
    "retention-administrator",
    "account-owner-break-glass",
}
EXPECTED_CLASSES = {
    "release-control",
    "watershed-vector",
    "thematic-tabular",
    "rhessys-input",
    "rhessys-output",
    "validation-evidence",
}
EXPECTED_FAILURES = {
    "partial-upload",
    "hash-collision",
    "stale-cache",
    "revoked-credentials",
    "provider-outage",
    "accidental-deletion",
    "restore-active-two-rollbacks",
    "compromised-publisher",
    "lifecycle-misconfiguration",
}
EXPECTED_CREDENTIAL_ENVIRONMENT = {
    "UWA_ARTIFACT_ENDPOINT",
    "UWA_ARTIFACT_BUCKET",
    "UWA_ARTIFACT_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
}
ADMIN_CAPABILITIES = {
    "deleteFiles",
    "writeBucketRetentions",
    "writeFileRetentions",
    "writeFileLegalHolds",
    "bypassGovernance",
    "bucket-configuration",
    "key-administration",
}
SHA_KEY_REGEX = r"^v1/blobs/sha256/[a-f0-9]{2}/[a-f0-9]{64}$"


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
    provider = policy["provider"]
    require(provider["id"] == "backblaze-b2", "provider must be backblaze-b2")
    require(provider["api"] == "s3-compatible", "provider API must be S3-compatible")
    endpoint = urlsplit(provider["endpoint_template"].replace("<assigned-us-region>", "us-west-000"))
    require(endpoint.scheme == "https", "provider endpoint must use HTTPS")
    require(endpoint.username is None and endpoint.password is None, "provider endpoint contains credentials")
    require(not endpoint.query and not endpoint.fragment, "provider endpoint contains query or fragment")

    ownership = policy["ownership"]
    require(ownership["account"] == "project-controlled", "account ownership is not project-controlled")
    require(ownership["account_mfa_required"], "account MFA is required")
    require(ownership["offline_recovery_material_required"], "offline recovery material is required")
    require(ownership["public_bucket_prohibited"], "public buckets must be prohibited")

    environments = [bucket["environment"] for bucket in policy["buckets"]]
    require(environments == ["test", "production"], "exact test and production buckets are required")
    for bucket in policy["buckets"]:
        require(bucket["private"], f"{bucket['environment']} bucket must be private")
        require(
            bucket["object_lock_enabled_before_first_object"],
            f"{bucket['environment']} bucket must enable Object Lock before use",
        )
        require("<account-suffix>" in bucket["name_pattern"], "bucket name must include account suffix")

    encryption = policy["encryption"]
    require(encryption["at_rest"] == "SSE-B2-AES256", "default encryption must be SSE-B2 AES-256")
    require(encryption["default_bucket_encryption_required"], "default bucket encryption is required")
    require(not encryption["customer_managed_sse_c"], "SSE-C is outside the version-1 contract")
    require(encryption["in_transit"] == "TLS", "TLS transport is required")

    immutability = policy["immutability"]
    require(immutability["mode"] == "COMPLIANCE", "Object Lock must use COMPLIANCE mode")
    require(immutability["default_days"] >= 365, "Object Lock default must be at least 365 days")
    require(not immutability["governance_bypass_allowed"], "governance bypass must be prohibited")
    require(
        not immutability["lifecycle_may_delete_locked_objects"],
        "lifecycle may not delete locked objects",
    )

    key_layout = policy["key_layout"]
    require(key_layout["algorithm"] == "sha256", "key layout must use SHA-256")
    require(key_layout["regex"] == SHA_KEY_REGEX, "content-addressed key regex differs")
    re.compile(key_layout["regex"])
    require(not key_layout["mutable_alias_is_authority"], "mutable aliases cannot be authority")
    require(not key_layout["overwrite_allowed"], "content-addressed overwrite must be prohibited")

    roles = {role["role"]: role for role in policy["roles"]}
    require(set(roles) == EXPECTED_ROLES, "role coverage differs")
    for role in roles.values():
        require_unique(role["capabilities"], f"{role['role']} capabilities")
    publisher_capabilities = set(roles["publisher"]["capabilities"])
    require(
        publisher_capabilities == {"listFiles", "readFiles", "writeFiles"},
        "publisher capabilities exceed bounded read/write",
    )
    require(
        set(roles["runtime-reader"]["capabilities"]) == {"readFiles"},
        "runtime reader must have object read only",
    )
    require(
        not set(roles["deployment-reader"]["capabilities"]) & ADMIN_CAPABILITIES,
        "deployment reader has administrative capability",
    )
    retention_capabilities = set(roles["retention-administrator"]["capabilities"])
    require("deleteFiles" in retention_capabilities, "retention administrator needs exact delete")
    require("bypassGovernance" not in retention_capabilities, "retention administrator cannot bypass lock")
    require(
        not roles["account-owner-break-glass"]["deployed_to_application"],
        "break-glass credential cannot be deployed",
    )
    require(
        set(policy["credential_environment"]) == EXPECTED_CREDENTIAL_ENVIRONMENT,
        "credential environment names differ",
    )

    publication = policy["publication"]
    for field in (
        "streaming_multipart",
        "abort_failed_multipart",
        "verify_sha256_before_upload",
        "verify_sha256_after_upload",
        "verify_size_and_media_type",
        "existing_key_requires_full_verification",
    ):
        require(publication[field], f"publication control {field} is required")
    require(not publication["temporary_visible_key_allowed"], "temporary visible keys are prohibited")
    require(publication["orphan_multipart_max_age_hours"] <= 24, "orphan multipart cleanup exceeds 24 hours")

    retention = policy["retention"]
    require(retention["minimum_releases"] >= 3, "active plus two rollback releases are required")
    require(
        retention["required_release_roles"] == ["active", "rollback-1", "rollback-2"],
        "retained release roles differ",
    )
    require(retention["retained_release_ttl"] is None, "retained releases cannot have TTL")
    require(retention["gc_preview_required"], "GC preview is required")
    require(retention["gc_exact_reachability_required"], "GC exact reachability is required")
    require(retention["gc_requires_lock_expiry"], "GC must wait for lock expiry")

    cache = policy["cache"]
    for field in (
        "verify_sha256_on_every_hit",
        "download_to_unique_temporary_file",
        "atomic_promote_after_verification",
        "concurrent_readers_allowed",
        "provider_is_authority",
    ):
        require(cache[field], f"cache control {field} is required")
    require(not cache["content_entry_mutation_allowed"], "cache content mutation is prohibited")
    require(not cache["evict_during_active_build"], "cache eviction during active build is prohibited")

    recovery = policy["recovery"]
    require(recovery["mirror_host"] == "forest1", "independent recovery mirror must be on forest1")
    require(recovery["minimum_mirrored_releases"] >= 3, "mirror must contain active plus two rollbacks")
    require(recovery["verify_mirror_after_publication"], "mirror verification after publication is required")
    require(
        recovery["provider_outage_behavior"] == "fail-closed-without-active-state-change",
        "provider outage must fail closed",
    )
    require(recovery["quarterly_restore_drill_required"], "quarterly artifact restore drill is required")


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
        require(item["sensitivity"] in {"public", "public-sanitized"}, "artifact sensitivity must remain public")
        require(item["pii"] == "prohibited", f"{item['class_key']} must prohibit PII")
        require(item["residency"] == "united-states", f"{item['class_key']} residency differs")
        require("active-plus-two-rollbacks" in item["retention"], f"{item['class_key']} retention differs")
    require_unique(members, "artifact class members")


def validate_threat_review(document: dict[str, Any]) -> None:
    require(document["contract_version"] == 1, "threat-review contract version must be 1")
    cases = document["cases"]
    keys = [item["case_key"] for item in cases]
    require_unique(keys, "threat case keys")
    require(set(keys) == EXPECTED_FAILURES, "threat/failure coverage differs")
    for item in cases:
        for field in ("prevention", "detection", "response", "owner", "db10a_proof"):
            require(isinstance(item[field], str) and item[field], f"{item['case_key']} lacks {field}")
        require(item["owner"] in EXPECTED_ROLES, f"{item['case_key']} owner is unknown")


def validate_suite(contract_directory: Path = CONTRACT_DIRECTORY) -> dict[str, int]:
    policy = load_json(contract_directory / "artifact-store-policy.json")
    classes = load_json(contract_directory / "artifact-classes.json")
    threats = load_json(contract_directory / "threat-review.json")
    validate_policy(policy)
    validate_artifact_classes(classes)
    validate_threat_review(threats)
    return {
        "buckets": len(policy["buckets"]),
        "roles": len(policy["roles"]),
        "artifact_classes": len(classes["classes"]),
        "threat_cases": len(threats["cases"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the DB10 artifact-store contract.")
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
