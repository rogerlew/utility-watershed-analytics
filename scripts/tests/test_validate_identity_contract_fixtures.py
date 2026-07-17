from __future__ import annotations

import ast
import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate_identity_contract_fixtures.py"
FIXTURE_PATH = (
    ROOT
    / "docs"
    / "work-packages"
    / "20260717-db07-identity-metadata-contract"
    / "artifacts"
    / "identity-contract-fixtures.json"
)
SPEC = importlib.util.spec_from_file_location("validate_identity_contract_fixtures", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class IdentityContractFixtureTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_fixture_passes(self):
        summary = MODULE.validate_contract(self.document)
        self.assertEqual(summary["collections"], 4)
        self.assertEqual(summary["fields_per_collection"], 24)
        self.assertGreaterEqual(summary["accepted_scenarios"], 9)
        self.assertGreaterEqual(summary["rejected_scenarios"], 3)

    def test_duplicate_collection_key_fails(self):
        document = copy.deepcopy(self.document)
        document["collections"][1]["collection_key"] = document["collections"][0]["collection_key"]
        with self.assertRaisesRegex(MODULE.ContractError, "coverage mismatch|duplicate"):
            MODULE.validate_contract(document)

    def test_missing_field_authority_fails(self):
        document = copy.deepcopy(self.document)
        del document["collections"][0]["field_authority"]["geom"]
        with self.assertRaisesRegex(MODULE.ContractError, "field coverage mismatch"):
            MODULE.validate_contract(document)

    def test_watershed_model_field_coverage(self):
        model_path = ROOT / "server" / "server" / "watershed" / "models.py"
        module = ast.parse(model_path.read_text(encoding="utf-8"))
        watershed = next(
            node
            for node in module.body
            if isinstance(node, ast.ClassDef) and node.name == "Watershed"
        )
        model_fields = tuple(
            target.id
            for node in watershed.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        )
        self.assertEqual(model_fields, MODULE.EXPECTED_FIELDS)

    def test_invalid_key_fails(self):
        document = copy.deepcopy(self.document)
        document["collections"][0]["sample_watershed_keys"][0] = "Gate Creek"
        with self.assertRaisesRegex(MODULE.ContractError, "invalid syntax"):
            MODULE.validate_contract(document)

    def test_expected_decision_mismatch_fails(self):
        document = copy.deepcopy(self.document)
        document["scenarios"][0]["expected"] = {
            "decision": "reject",
            "code": "ambiguous-identity",
        }
        with self.assertRaisesRegex(MODULE.ContractError, "expected"):
            MODULE.validate_contract(document)

    def test_split_key_reuse_fails(self):
        document = copy.deepcopy(self.document)
        split = next(item for item in document["scenarios"] if item["kind"] == "split")
        split["after"]["watershed_keys"][0] = split["before"]["watershed_keys"][0]
        with self.assertRaisesRegex(MODULE.ContractError, "reused predecessor key"):
            MODULE.validate_contract(document)


if __name__ == "__main__":
    unittest.main()
