import json
import stat
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_database_release_status.py"
NOW = "2026-07-18T20:00:00Z"


class DatabaseReleaseStatusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="uwa-db27-status-")
        self.root = Path(self.temporary.name)
        self.attempts = self.root / "attempts"
        self.attempts.mkdir()
        self.documents = {
            "active": {
                "schema_version": 1,
                "state": "ACTIVE",
                "active_release": {
                    "release_id": "synthetic-db27",
                    "manifest_sha256": "a" * 64,
                    "data_contract": 1,
                    "activated_at": "2026-07-18T18:00:00Z",
                    "counts": {"watersheds": 2, "subcatchments": 3, "channels": 4, "capabilities": 1},
                },
            },
            "inventory": {
                "schema_version": 1,
                "release_id": "synthetic-db27",
                "manifest_sha256": "a" * 64,
                "counts": {"watersheds": 2, "subcatchments": 3, "channels": 4, "capabilities": 1},
                "captured_at": "2026-07-18T19:00:00Z",
                "artifact_published_at": "2026-07-18T18:00:00Z",
            },
            "storage": {
                "schema_version": 1,
                "observed_at": "2026-07-18T20:00:00Z",
                "capacity_bytes": 2_000_000,
                "available_bytes": 1_500_000,
                "artifact_bytes": 200_000,
                "previous_artifact_bytes": 150_000,
            },
            "backup": {
                "schema_version": 1,
                "snapshot_id": "synthetic-snapshot",
                "latest_completed_at": "2026-07-18T19:00:00Z",
            },
        }

    def tearDown(self):
        self.temporary.cleanup()

    def run_status(self, mutation=None, attempt=None):
        documents = deepcopy(self.documents)
        if mutation:
            mutation(documents)
        paths = {}
        for name, document in documents.items():
            path = self.root / f"{name}.json"
            path.write_text(json.dumps(document) + "\n")
            path.chmod(0o600 if name in {"storage", "backup"} else 0o644)
            paths[name] = path
        if attempt:
            operation = self.attempts / "operation"
            operation.mkdir(exist_ok=True)
            state = operation / "state.json"
            state.write_text(json.dumps(attempt) + "\n")
            state.chmod(0o600)
        report = self.root / "reports" / "status.json"
        completed = subprocess.run([
            str(SCRIPT),
            "--active-status", str(paths["active"]),
            "--inventory-snapshot", str(paths["inventory"]),
            "--storage-snapshot", str(paths["storage"]),
            "--backup-snapshot", str(paths["backup"]),
            "--attempt-root", str(self.attempts),
            "--report", str(report),
            "--minimum-available-bytes", "1000000",
            "--maximum-growth-bytes", "100000",
            "--maximum-artifact-age-hours", "24",
            "--maximum-backup-age-hours", "25",
            "--abandoned-attempt-hours", "2",
            "--now", NOW,
        ], capture_output=True, text=True)
        return completed, report

    def test_healthy_status_and_private_report(self):
        completed, report = self.run_status()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "passed")
        self.assertEqual(stat.S_IMODE(report.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(report.parent.stat().st_mode), 0o700)

    def test_monitor_failure_matrix(self):
        cases = {
            "active mismatch": lambda docs: docs["active"]["active_release"].update(release_id="other"),
            "inventory mismatch": lambda docs: docs["inventory"]["counts"].update(watersheds=9),
            "capacity": lambda docs: docs["storage"].update(available_bytes=1),
            "growth": lambda docs: docs["storage"].update(artifact_bytes=500_000),
            "artifact age": lambda docs: docs["inventory"].update(artifact_published_at="2026-07-01T00:00:00Z"),
            "backup age": lambda docs: docs["backup"].update(latest_completed_at="2026-07-01T00:00:00Z"),
        }
        for name, mutation in cases.items():
            with self.subTest(name=name):
                completed, report = self.run_status(mutation)
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertEqual(json.loads(report.read_text())["status"], "failed")

        completed, _ = self.run_status(attempt={
            "status": "failed",
            "updated_at": "2026-07-18T19:00:00Z",
        })
        self.assertEqual(completed.returncode, 1)
        completed, _ = self.run_status(attempt={
            "status": "running",
            "updated_at": "2026-07-18T10:00:00Z",
        })
        self.assertEqual(completed.returncode, 1)

    def test_malformed_broad_private_and_secret_inputs_are_invalid(self):
        completed, _ = self.run_status(lambda docs: docs["backup"].update(token="forbidden"))
        self.assertEqual(completed.returncode, 2)

        completed, _ = self.run_status(lambda docs: docs["active"].update(state="BROKEN"))
        self.assertEqual(completed.returncode, 2)

        path = self.root / "storage.json"
        path.chmod(0o644)
        completed = subprocess.run([
            str(SCRIPT), "--active-status", str(self.root / "active.json"),
            "--inventory-snapshot", str(self.root / "inventory.json"),
            "--storage-snapshot", str(path),
            "--backup-snapshot", str(self.root / "backup.json"),
            "--attempt-root", str(self.attempts),
            "--report", str(self.root / "report.json"),
        ], capture_output=True)
        self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
