from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPOSITORY_ROOT / "scripts" / "accept_source_preparation.py"


class SourcePreparationAcceptanceTests(unittest.TestCase):
    def test_wrapper_passes_and_removes_temporary_subtree(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            completed = subprocess.run(
                ["python3", str(SCRIPT), "--workspace", str(workspace)],
                cwd=REPOSITORY_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "passed")
            self.assertTrue(result["temporary_subtree_removed"])
            self.assertEqual(list(workspace.iterdir()), [])

    def test_wrapper_refuses_nonapproved_required_namespace(self):
        with tempfile.TemporaryDirectory() as temporary:
            completed = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--workspace",
                    temporary,
                    "--require-test-namespace",
                ],
                cwd=REPOSITORY_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertEqual(json.loads(completed.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
