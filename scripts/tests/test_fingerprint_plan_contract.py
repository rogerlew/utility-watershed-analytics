from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FINGERPRINTS = load_module("release_fingerprints", SCRIPTS / "release_fingerprints.py")
CONTRACT = load_module(
    "validate_fingerprint_plan_contract",
    SCRIPTS / "validate_fingerprint_plan_contract.py",
)


class FingerprintPlanContractTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = (
            ROOT / "data-releases" / "fixtures" / "v1" / "fingerprint-plans"
        )
        self.schemas = ROOT / "data-releases" / "schema" / "v1" / "plans"
        self.forward = FINGERPRINTS.load_json(self.fixtures / "plans" / "forward.json")
        self.inverse = FINGERPRINTS.load_json(
            self.fixtures / "plans" / "exact-inverse.json"
        )

    def test_full_fixture_suite_passes(self):
        self.assertEqual(
            CONTRACT.validate_suite(self.fixtures, self.schemas),
            {
                "fingerprint_subjects": 5,
                "plan_schemas": 4,
                "plans": 3,
                "semantic_mutations": 5,
            },
        )

    def test_canonical_formatting_and_object_order_are_irrelevant(self):
        first = {"z": [True, None], "a": {"number": Decimal("1.00")}}
        second = json.loads(
            '{"a":{"number":1.0},"z":[true,null]}',
            parse_float=Decimal,
        )
        self.assertEqual(
            FINGERPRINTS.canonical_bytes(first),
            FINGERPRINTS.canonical_bytes(second),
        )

    def test_unicode_normalization_is_stable(self):
        self.assertEqual(
            FINGERPRINTS.canonical_bytes({"name": "Caf\u00e9"}),
            FINGERPRINTS.canonical_bytes({"name": "Cafe\u0301"}),
        )

    def test_binary_float_is_rejected(self):
        with self.assertRaisesRegex(FINGERPRINTS.FingerprintError, "floating-point"):
            FINGERPRINTS.canonical_bytes({"value": 1.5})

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaisesRegex(FINGERPRINTS.FingerprintError, "duplicate JSON"):
            json.loads('{"value":1,"value":2}', object_pairs_hook=FINGERPRINTS.unique_object)

    def test_repeated_processes_match_golden_artifact(self):
        command = [
            sys.executable,
            str(SCRIPTS / "release_fingerprints.py"),
            "artifact",
            str(
                ROOT
                / "data-releases"
                / "fixtures"
                / "v1"
                / "valid"
                / "artifact-reference.json"
            ),
        ]
        first = subprocess.run(command, check=True, capture_output=True, text=True)
        second = subprocess.run(command, check=True, capture_output=True, text=True)
        golden = FINGERPRINTS.load_json(
            self.fixtures / "golden-fingerprints.json"
        )
        self.assertEqual(first.stdout.strip(), golden["artifact"])
        self.assertEqual(first.stdout, second.stdout)

    def test_wrong_base_replay_fails(self):
        wrong_base = FINGERPRINTS.load_json(self.fixtures / "wrong-base.json")
        with self.assertRaisesRegex(CONTRACT.ContractError, "exactly match"):
            CONTRACT.assert_plan_base(self.forward, wrong_base)

    def test_inverse_delta_mutation_fails(self):
        inverse = copy.deepcopy(self.inverse)
        inverse["actions"][0]["row_delta"]["subcatchments"] = 1
        with self.assertRaisesRegex(CONTRACT.ContractError, "not negated"):
            CONTRACT.validate_exact_inverse(self.forward, inverse)

    def test_inverse_materializer_mismatch_fails(self):
        inverse = copy.deepcopy(self.inverse)
        inverse["materializer"]["git_commit"] = "f" * 40
        with self.assertRaisesRegex(CONTRACT.ContractError, "materializer differs"):
            CONTRACT.validate_exact_inverse(self.forward, inverse)

    def test_unknown_fingerprint_version_fails_schema(self):
        forward = copy.deepcopy(self.forward)
        forward["fingerprint_version"] = 2
        validator = CONTRACT.build_plan_validators(self.schemas)[
            "forward-plan.schema.json"
        ]
        self.assertTrue(
            any(error.validator == "const" for error in validator.iter_errors(forward))
        )

    def test_wildcard_action_key_fails_schema(self):
        forward = copy.deepcopy(self.forward)
        forward["actions"][0]["watershed_key"] = "example-*"
        validator = CONTRACT.build_plan_validators(self.schemas)[
            "forward-plan.schema.json"
        ]
        self.assertTrue(
            any(
                nested.validator == "pattern"
                for error in validator.iter_errors(forward)
                for nested in [error, *error.context]
            )
        )

    def test_incomplete_base_state_fails_schema(self):
        forward = copy.deepcopy(self.forward)
        del forward["base"]["manifest_sha256"]
        validator = CONTRACT.build_plan_validators(self.schemas)[
            "forward-plan.schema.json"
        ]
        self.assertTrue(
            any(
                nested.validator == "required"
                for error in validator.iter_errors(forward)
                for nested in [error, *error.context]
            )
        )


if __name__ == "__main__":
    unittest.main()
