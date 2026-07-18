from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate_release_schemas.py"
SPEC = importlib.util.spec_from_file_location("validate_release_schemas", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReleaseSchemaTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = ROOT / "data-releases" / "fixtures" / "v1"
        self.schemas = ROOT / "data-releases" / "schema" / "v1"

    def write_fixture_copy(self, mutate):
        temporary = tempfile.TemporaryDirectory()
        destination = Path(temporary.name)
        for source in self.fixtures.rglob("*.json"):
            relative = source.relative_to(self.fixtures)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        mutate(destination)
        return temporary, destination

    def test_fixture_suite_passes(self):
        summary = MODULE.validate_suite(self.fixtures, self.schemas)
        self.assertEqual(summary, {"schemas": 7, "valid_cases": 7, "invalid_cases": 9})

    def test_duplicate_collection_key_fails(self):
        document = json.loads((self.fixtures / "valid" / "release-manifest.json").read_text(encoding="utf-8"))
        document["collections"].append(copy.deepcopy(document["collections"][0]))
        with self.assertRaisesRegex(MODULE.ContractError, "collection_key.*duplicates"):
            MODULE.validate_release_manifest(document)

    def test_duplicate_runid_fails(self):
        document = json.loads((self.fixtures / "valid" / "batch-member-index.json").read_text(encoding="utf-8"))
        document["members"][1]["runid"] = document["members"][0]["runid"]
        with self.assertRaisesRegex(MODULE.ContractError, "runid.*duplicates"):
            MODULE.validate_batch_member_index(document)

    def test_raw_token_key_fails_secret_boundary(self):
        with self.assertRaisesRegex(MODULE.ContractError, "prohibited credential-bearing key"):
            MODULE.validate_safe_content({"authentication": {"token": "example"}})

    def test_missing_schema_coverage_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            schema_directory = Path(temporary)
            source = self.schemas / "artifact-reference.schema.json"
            (schema_directory / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.ContractError, "schema coverage mismatch"):
                MODULE.build_validators(schema_directory)

    def test_release_index_membership_mismatch_fails(self):
        def mutate(directory):
            path = directory / "valid" / "release-manifest.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["collections"][0]["watershed_keys"].reverse()
            path.write_text(json.dumps(document), encoding="utf-8")

        temporary, directory = self.write_fixture_copy(mutate)
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(MODULE.ContractError, "membership or order differs"):
            MODULE.validate_suite(directory, self.schemas)

    def test_structural_negative_that_becomes_valid_fails(self):
        def mutate(directory):
            path = directory / "invalid" / "incompatible-version.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["data_contract"] = 1
            path.write_text(json.dumps(document), encoding="utf-8")

        temporary, directory = self.write_fixture_copy(mutate)
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(MODULE.ContractError, "did not fail with const"):
            MODULE.validate_suite(directory, self.schemas)


if __name__ == "__main__":
    unittest.main()
