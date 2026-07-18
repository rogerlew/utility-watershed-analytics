from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate_artifact_store_contract.py"
SPEC = importlib.util.spec_from_file_location("validate_artifact_store_contract", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ArtifactStoreContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / "data-releases" / "storage-contract" / "v1"
        self.policy = json.loads((self.directory / "artifact-store-policy.json").read_text(encoding="utf-8"))
        self.classes = json.loads((self.directory / "artifact-classes.json").read_text(encoding="utf-8"))
        self.threats = json.loads((self.directory / "threat-review.json").read_text(encoding="utf-8"))

    def test_complete_contract_passes(self):
        self.assertEqual(
            MODULE.validate_suite(self.directory),
            {"buckets": 2, "roles": 5, "artifact_classes": 6, "threat_cases": 9},
        )

    def test_provider_change_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["provider"]["id"] = "unreviewed-provider"
        with self.assertRaisesRegex(MODULE.ContractError, "backblaze-b2"):
            MODULE.validate_policy(policy)

    def test_publisher_delete_capability_fails(self):
        policy = copy.deepcopy(self.policy)
        publisher = next(role for role in policy["roles"] if role["role"] == "publisher")
        publisher["capabilities"].append("deleteFiles")
        with self.assertRaisesRegex(MODULE.ContractError, "publisher capabilities"):
            MODULE.validate_policy(policy)

    def test_short_object_lock_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["immutability"]["default_days"] = 30
        with self.assertRaisesRegex(MODULE.ContractError, "at least 365"):
            MODULE.validate_policy(policy)

    def test_two_release_retention_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["retention"]["minimum_releases"] = 2
        with self.assertRaisesRegex(MODULE.ContractError, "active plus two"):
            MODULE.validate_policy(policy)

    def test_missing_artifact_class_fails(self):
        classes = copy.deepcopy(self.classes)
        classes["classes"].pop()
        with self.assertRaisesRegex(MODULE.ContractError, "class coverage"):
            MODULE.validate_artifact_classes(classes)

    def test_missing_required_failure_fails(self):
        threats = copy.deepcopy(self.threats)
        threats["cases"] = [
            item for item in threats["cases"] if item["case_key"] != "provider-outage"
        ]
        with self.assertRaisesRegex(MODULE.ContractError, "failure coverage"):
            MODULE.validate_threat_review(threats)

    def test_mutable_key_authority_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["key_layout"]["mutable_alias_is_authority"] = True
        with self.assertRaisesRegex(MODULE.ContractError, "mutable aliases"):
            MODULE.validate_policy(policy)

    def test_incomplete_recovery_mirror_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["recovery"]["minimum_mirrored_releases"] = 1
        with self.assertRaisesRegex(MODULE.ContractError, "active plus two"):
            MODULE.validate_policy(policy)

    def test_public_bucket_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["buckets"][1]["private"] = False
        with self.assertRaisesRegex(MODULE.ContractError, "production bucket must be private"):
            MODULE.validate_policy(policy)


if __name__ == "__main__":
    unittest.main()
