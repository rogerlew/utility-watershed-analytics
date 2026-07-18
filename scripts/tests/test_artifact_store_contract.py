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
        self.policy = json.loads((self.directory / "artifact-store-policy.json").read_text())
        self.classes = json.loads((self.directory / "artifact-classes.json").read_text())
        self.threats = json.loads((self.directory / "threat-review.json").read_text())

    def test_complete_contract_passes(self):
        self.assertEqual(
            MODULE.validate_suite(self.directory),
            {"namespaces": 2, "operators": 1, "artifact_classes": 6, "failure_cases": 7},
        )

    def test_paid_provider_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["storage"]["paid_provider_required"] = True
        with self.assertRaisesRegex(MODULE.ContractError, "paid provider"):
            MODULE.validate_policy(policy)

    def test_wrong_host_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["storage"]["host"] = "other-host"
        with self.assertRaisesRegex(MODULE.ContractError, "forest1"):
            MODULE.validate_policy(policy)

    def test_group_readable_directory_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["ownership"]["directory_mode"] = "0750"
        with self.assertRaisesRegex(MODULE.ContractError, "0700"):
            MODULE.validate_policy(policy)

    def test_two_release_retention_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["retention"]["minimum_releases"] = 2
        with self.assertRaisesRegex(MODULE.ContractError, "active plus two"):
            MODULE.validate_policy(policy)

    def test_automatic_deletion_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["retention"]["automatic_deletion_allowed"] = True
        with self.assertRaisesRegex(MODULE.ContractError, "automatic deletion"):
            MODULE.validate_policy(policy)

    def test_missing_artifact_class_fails(self):
        classes = copy.deepcopy(self.classes)
        classes["classes"].pop()
        with self.assertRaisesRegex(MODULE.ContractError, "class coverage"):
            MODULE.validate_artifact_classes(classes)

    def test_missing_required_failure_fails(self):
        threats = copy.deepcopy(self.threats)
        threats["cases"] = [item for item in threats["cases"] if item["case_key"] != "storage-full"]
        with self.assertRaisesRegex(MODULE.ContractError, "failure coverage"):
            MODULE.validate_threat_review(threats)

    def test_mutable_key_authority_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["key_layout"]["mutable_alias_is_authority"] = True
        with self.assertRaisesRegex(MODULE.ContractError, "mutable aliases"):
            MODULE.validate_policy(policy)

    def test_low_free_space_floor_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["monitoring"]["minimum_free_bytes"] = 1
        with self.assertRaisesRegex(MODULE.ContractError, "100 GiB"):
            MODULE.validate_policy(policy)


if __name__ == "__main__":
    unittest.main()
