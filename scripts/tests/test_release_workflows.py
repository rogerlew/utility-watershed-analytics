import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.validate_release_workflows as validator


ROOT = Path(__file__).resolve().parents[2]


class ReleaseWorkflowPolicyTests(unittest.TestCase):
    def test_repository_workflows_pass(self):
        completed = subprocess.run(
            ["python3", str(ROOT / "scripts" / "validate_release_workflows.py")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def assert_rejected(self, filename, mutation):
        with tempfile.TemporaryDirectory(prefix="uwa-db27-workflows-") as temporary:
            destination = Path(temporary)
            for source in (ROOT / ".github" / "workflows").glob("*.yml"):
                content = source.read_text()
                if source.name == filename:
                    content = mutation(content)
                (destination / source.name).write_text(content)
            with patch.object(validator, "WORKFLOWS", destination):
                with self.assertRaises(SystemExit):
                    validator.main()

    def test_push_environment_action_and_hash_bypasses_fail(self):
        self.assert_rejected(
            "data-release-deploy.yml",
            lambda value: value.replace("  workflow_dispatch:\n", "  push:\n    branches: [main]\n  workflow_dispatch:\n", 1),
        )
        self.assert_rejected(
            "data-release-prepare.yml",
            lambda value: value.replace("    runs-on: ubuntu-latest", "    runs-on: self-hosted", 1),
        )
        self.assert_rejected(
            "data-release-rollback.yml",
            lambda value: value.replace("production-data-rollback", "production-data-deploy"),
        )
        self.assert_rejected(
            "data-release-deploy.yml",
            lambda value: value.replace("--action deploy", "--action rollback"),
        )
        self.assert_rejected(
            "data-release-deploy.yml",
            lambda value: value.replace("      authorization_sha256:\n", "      removed_authorization_sha256:\n", 1),
        )
        self.assert_rejected(
            "deploy.yml",
            lambda value: value.replace("scripts/deploy_application.sh", "scripts/deploy_database.sh"),
        )


if __name__ == "__main__":
    unittest.main()
