from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "accept_artifact_client.py"
SPEC = importlib.util.spec_from_file_location("accept_artifact_client", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ArtifactClientAcceptanceTests(unittest.TestCase):
    def test_acceptance_passes_and_removes_subtree(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            result = MODULE.run_acceptance(workspace)
            self.assertEqual(result["status"], "passed")
            self.assertTrue(result["temporary_subtree_removed"])
            self.assertTrue(all(result["checks"].values()))
            self.assertEqual(list(workspace.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
