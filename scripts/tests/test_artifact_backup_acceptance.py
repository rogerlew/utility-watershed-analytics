from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "accept_artifact_backup.py"
SPEC = importlib.util.spec_from_file_location("accept_artifact_backup", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ArtifactBackupAcceptanceTests(unittest.TestCase):
    def test_acceptance_passes_in_clean_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "backup" / "v1"
            result = MODULE.accept(root, 1)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["backup"]["releases"], 3)
            self.assertEqual(result["restore"], result["backup"])
            self.assertTrue(result["production_namespace_empty"])

    def test_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "backup" / "v1"
            first = MODULE.accept(root, 1)
            second = MODULE.accept(root, 1)
            self.assertEqual(first["backup"], second["backup"])

    def test_free_space_floor_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "backup" / "v1"
            with self.assertRaisesRegex(MODULE.AcceptanceError, "free space"):
                MODULE.accept(root, 2**63)

    def test_existing_object_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.write_bytes(b"expected")
            digest = MODULE.sha256_file(source)
            destination = root / "namespace" / "objects" / "sha256" / digest[:2] / digest
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"wrong")
            with self.assertRaisesRegex(MODULE.AcceptanceError, "does not match"):
                MODULE.publish_object(source, root / "namespace")


if __name__ == "__main__":
    unittest.main()
