import hashlib
import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "release_authorization.py"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReleaseAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="uwa-db27-auth-")
        self.root = Path(self.temporary.name)
        self.operation_id = "db27-synthetic-deploy"
        self.release_id = "synthetic-db27"
        self.manifest = "a" * 64
        self.paths = {}
        for name, filename in {
            "release": "release.json",
            "members": "members.json",
            "forward_plan": "forward.json",
            "inverse_plan": "inverse.json",
        }.items():
            path = self.root / filename
            document = {"schema_version": 1, "kind": name}
            if name == "release":
                document.update(release_id=self.release_id, manifest_sha256=self.manifest)
            path.write_text(json.dumps(document, sort_keys=True) + "\n")
            self.paths[name] = path
        self.request = self.root / "request-source.json"
        self.request.write_text(json.dumps({
            "schema_version": 1,
            "operation_id": self.operation_id,
            "release_id": self.release_id,
            "expected_base_manifest": "EMPTY",
            "tool_image": "example.invalid/server@sha256:" + "b" * 64,
            "tool_image_id": "sha256:" + "c" * 64,
            "application_git_commit": "d" * 40,
            "materializer_git_commit": "e" * 40,
            "inputs": {
                name: {
                    "path": f"/srv/utility-watershed-analytics/releases/{self.operation_id}/{path.name}",
                    "sha256": digest(path),
                }
                for name, path in self.paths.items()
            },
        }, sort_keys=True) + "\n")
        self.clean_build = self.root / "clean-build.json"
        self.clean_build.write_text(json.dumps({
            "status": "passed",
            "release_id": self.release_id,
            "manifest_sha256": self.manifest,
        }, sort_keys=True) + "\n")
        self.inventory = self.root / "inventory.json"
        self.inventory.write_text(json.dumps({
            "schema_version": 1,
            "release_id": self.release_id,
            "manifest_sha256": self.manifest,
            "counts": {"watersheds": 2, "subcatchments": 3, "channels": 4, "capabilities": 1},
        }, sort_keys=True) + "\n")

    def tearDown(self):
        for path in self.root.rglob("*"):
            if path.is_file():
                path.chmod(0o600)
        self.temporary.cleanup()

    def prepare_command(self, output, action="deploy"):
        return [
            str(SCRIPT), "prepare", "--action", action,
            "--source-commit", "f" * 40,
            "--preparation-run-id", "run-123",
            "--source-root", str(self.root),
            "--output", str(output),
            "--request", str(self.request),
            "--release", str(self.paths["release"]),
            "--members", str(self.paths["members"]),
            "--forward-plan", str(self.paths["forward_plan"]),
            "--inverse-plan", str(self.paths["inverse_plan"]),
            "--clean-build-report", str(self.clean_build),
            "--inventory-snapshot", str(self.inventory),
        ]

    def prepare(self, name="bundle", action="deploy"):
        output = self.root / name
        completed = subprocess.run(self.prepare_command(output, action), capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return output, json.loads(completed.stdout)

    def verify(self, bundle, result, action="deploy", operation_id=None, source_commit=None):
        return subprocess.run([
            str(SCRIPT), "verify", "--action", action,
            "--bundle", str(bundle),
            "--authorization-sha256", result["authorization_sha256"],
            "--operation-id", operation_id or self.operation_id,
            "--source-commit", source_commit or "f" * 40,
            "--result", str(self.root / "verification" / "result.json"),
        ], capture_output=True, text=True)

    def test_deterministic_deploy_and_distinct_rollback_bundles(self):
        first, first_result = self.prepare("first")
        second, second_result = self.prepare("second")
        self.assertEqual(first_result["authorization_sha256"], second_result["authorization_sha256"])
        verified = self.verify(first, first_result)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["action"], "deploy")
        self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o700)
        for path in first.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)

        rollback, rollback_result = self.prepare("rollback", "rollback")
        wrong_path = self.verify(rollback, rollback_result, "deploy")
        self.assertNotEqual(wrong_path.returncode, 0)
        accepted = self.verify(rollback, rollback_result, "rollback")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_mutation_hash_role_and_coordinate_fail_closed(self):
        bundle, result = self.prepare()
        target = bundle / "members.json"
        target.chmod(0o600)
        target.write_text("{}\n")
        target.chmod(0o400)
        self.assertNotEqual(self.verify(bundle, result).returncode, 0)

        bundle, result = self.prepare("role-bundle")
        self.assertNotEqual(self.verify(bundle, result, "rollback").returncode, 0)
        self.assertNotEqual(self.verify(bundle, result, operation_id="other-operation").returncode, 0)
        self.assertNotEqual(self.verify(bundle, result, source_commit="0" * 40).returncode, 0)
        wrong_hash = {**result, "authorization_sha256": "0" * 64}
        self.assertNotEqual(self.verify(bundle, wrong_hash).returncode, 0)

        writable = bundle / "release.json"
        writable.chmod(0o600)
        self.assertNotEqual(self.verify(bundle, result).returncode, 0)

    def test_source_symlink_mismatch_and_secret_keys_fail_closed(self):
        symlink = self.root / "symlink-release.json"
        symlink.symlink_to(self.paths["release"])
        command = self.prepare_command(self.root / "symlink-bundle")
        command[command.index("--release") + 1] = str(symlink)
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

        self.paths["members"].write_text(json.dumps({"token": "not-allowed"}) + "\n")
        self.assertNotEqual(
            subprocess.run(self.prepare_command(self.root / "secret-bundle"), capture_output=True).returncode,
            0,
        )

        self.paths["members"].write_text('{"schema_version":1,"kind":"members"}\n')
        self.request.write_text(self.request.read_text().replace(digest(self.paths["members"]), "0" * 64))
        self.assertNotEqual(
            subprocess.run(self.prepare_command(self.root / "mismatch-bundle"), capture_output=True).returncode,
            0,
        )


if __name__ == "__main__":
    unittest.main()
