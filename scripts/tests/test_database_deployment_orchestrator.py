#!/usr/bin/env python3

import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "deploy_database.sh"
LOCK = ROOT / "scripts" / "with_operation_lock.sh"
FIXED_ADAPTER = ROOT / "scripts" / "database_deployment_phase.sh"


ADAPTER = r'''#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

phase, request_path, state_path, operation_path, secret_path = sys.argv[1:]
operation = Path(operation_path)
scenario = Path(secret_path).read_text().strip()
with (operation / "calls").open("a", encoding="utf-8") as stream:
    stream.write(phase + "\n")
state = json.loads(Path(state_path).read_text())

if scenario in {"interrupt", "crash", "reboot"} and phase == "stage":
    marker = operation / "stage-waited"
    if not marker.exists():
        marker.write_text("1")
        time.sleep(60)
if scenario == "failed_backup" and phase == "backup":
    raise SystemExit(41)
if scenario == "stale_base" and phase == "compatibility":
    raise SystemExit(42)
if scenario in {"failed_smoke", "rollback_failure"} and phase == "smoke":
    raise SystemExit(43)
if scenario == "rollback_failure" and phase == "rollback":
    raise SystemExit(44)
if scenario == "archive_failure" and phase == "archive":
    raise SystemExit(45)

result = {"status": "passed"}
if scenario == "secret_result" and phase == "preflight":
    result["token"] = "must-not-persist"
if phase == "classify":
    result["outcome"] = "noop" if scenario == "noop" else "apply"
elif phase == "backup":
    result["backup_sha256"] = hashlib.sha256(b"fixture-backup").hexdigest()
elif phase == "publish":
    result.update(verified=True, snapshot_id="fixture-snapshot")
elif phase == "apply":
    result["activated"] = True
elif phase == "rollback":
    result["rolled_back"] = True
elif phase == "archive":
    archive = Path(os.environ["UWA_DB_DEPLOY_REPORT_ARCHIVE"])
    archive.mkdir(parents=True, exist_ok=True)
    shutil.copy2(operation / "report.json", archive / f"{operation.name}.json")
elif phase == "cleanup":
    result["retention_days"] = int(os.environ["UWA_DB_DEPLOY_REPORT_RETENTION_DAYS"])
print(json.dumps(result, sort_keys=True))
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OrchestratorAcceptance(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="uwa-db26-")
        self.root = Path(self.temporary.name)
        self.state_root = self.root / "state"
        self.archive = self.root / "forest1-report-archive"
        self.lock_file = self.root / "operations.lock"
        self.lock_file.touch(mode=0o660)
        self.adapter = self.root / "adapter.py"
        self.adapter.write_text(ADAPTER)
        self.adapter.chmod(0o700)
        self.inputs = {}
        for name in ("release", "members", "forward_plan", "inverse_plan"):
            path = self.root / f"{name}.json"
            path.write_text(json.dumps({"kind": name}) + "\n")
            path.chmod(0o400)
            self.inputs[name] = {"path": str(path), "sha256": digest(path)}

    def tearDown(self):
        for path in self.root.rglob("*"):
            if path.is_file():
                path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        self.temporary.cleanup()

    def command(self, operation_id, scenario):
        secret = self.root / f"{operation_id}.secret"
        secret.write_text(scenario)
        secret.chmod(0o600)
        request = self.root / f"{operation_id}.json"
        request.write_text(json.dumps({
            "schema_version": 1,
            "operation_id": operation_id,
            "release_id": "synthetic-20260718-db26",
            "expected_base_manifest": "EMPTY",
            "tool_image": "example.invalid/uwa@sha256:" + "a" * 64,
            "tool_image_id": "sha256:" + "b" * 64,
            "application_git_commit": "c" * 40,
            "materializer_git_commit": "d" * 40,
            "inputs": self.inputs,
        }, sort_keys=True) + "\n")
        request.chmod(0o400)
        return [
            str(LOCK), "--lock-file", str(self.lock_file), "--mode", "exclusive", "--",
            str(DEPLOY), "--request", str(request), "--request-sha256", digest(request),
            "--secret-file", str(secret), "--state-root", str(self.state_root),
            "--report-archive", str(self.archive), "--retention-days", "30",
            "--phase-timeout", "120", "--adapter", str(self.adapter),
        ]

    def run_operation(self, operation_id, scenario, expected=0):
        completed = subprocess.run(
            self.command(operation_id, scenario),
            env={**os.environ, "UWA_DB_DEPLOY_TEST_MODE": "1"},
            capture_output=True,
            text=True,
            timeout=150,
        )
        self.assertEqual(completed.returncode, expected, completed.stderr)
        return json.loads((self.state_root / operation_id / "state.json").read_text())

    def calls(self, operation_id):
        return (self.state_root / operation_id / "calls").read_text().splitlines()

    def test_fixed_adapter_contract(self):
        phase_root = self.root / "phases"
        phase_root.mkdir()
        phase = phase_root / "preflight"
        phase.write_text("#!/bin/sh\nprintf '{\"status\":\"passed\"}\\n'\n")
        phase.chmod(0o700)
        request = self.root / "adapter-request"
        state = self.root / "adapter-state"
        secret = self.root / "adapter-secret"
        for path in (request, state, secret):
            path.write_text("fixture")
        operation = self.root / "adapter-operation"
        operation.mkdir()
        arguments = [str(FIXED_ADAPTER), "preflight", str(request), str(state), str(operation), str(secret)]
        accepted = subprocess.run(
            arguments,
            env={
                **os.environ,
                "UWA_DB_DEPLOY_TEST_MODE": "1",
                "UWA_DB_DEPLOY_PHASE_ROOT": str(phase_root),
            },
            capture_output=True,
            text=True,
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(json.loads(accepted.stdout)["status"], "passed")
        rejected = subprocess.run(
            arguments,
            env={**os.environ, "UWA_DB_DEPLOY_PHASE_ROOT": str(phase_root)},
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("explicit test mode", rejected.stderr)

    def test_success_noop_and_failures(self):
        expired = self.state_root / "expired-terminal"
        expired.mkdir(parents=True)
        expired_state = expired / "state.json"
        expired_state.write_text(json.dumps({
            "status": "succeeded",
            "completed_at": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
        }))
        expired_state.chmod(0o600)
        success = self.run_operation("success", "success")
        self.assertEqual(success["status"], "succeeded")
        self.assertTrue(success["activated"])
        self.assertTrue((self.archive / "success.json").is_file())
        self.assertFalse(expired.exists())
        operation = self.state_root / "success"
        self.assertEqual(stat.S_IMODE(operation.stat().st_mode), 0o700)
        for private_file in (
            operation / "state.json",
            operation / "report.json",
            operation / "deployment.log",
            operation / "results" / "apply.json",
        ):
            self.assertEqual(stat.S_IMODE(private_file.stat().st_mode), 0o600)

        noop = self.run_operation("noop", "noop")
        self.assertEqual(noop["status"], "noop")
        self.assertNotIn("backup", self.calls("noop"))
        self.assertNotIn("apply", self.calls("noop"))

        failed_backup = self.run_operation("failed-backup", "failed_backup", 1)
        self.assertEqual(failed_backup["status"], "failed")
        self.assertFalse(failed_backup["rollback_attempted"])
        self.assertNotIn("apply", self.calls("failed-backup"))

        stale = self.run_operation("stale-base", "stale_base", 1)
        self.assertEqual(stale["failure_phase"], "compatibility")
        self.assertNotIn("backup", self.calls("stale-base"))

        rolled_back = self.run_operation("failed-smoke", "failed_smoke", 2)
        self.assertEqual(rolled_back["status"], "rolled_back")
        self.assertIn("rollback", self.calls("failed-smoke"))
        self.assertIn("rollback_smoke", self.calls("failed-smoke"))

        rollback_failed = self.run_operation("rollback-failure", "rollback_failure", 3)
        self.assertEqual(rollback_failed["status"], "rollback_failed")

        secret_result = self.run_operation("secret-result", "secret_result", 1)
        self.assertEqual(secret_result["status"], "failed")
        operation_text = "".join(
            path.read_text(errors="replace")
            for path in (self.state_root / "secret-result").rglob("*")
            if path.is_file()
        )
        self.assertNotIn("must-not-persist", operation_text)

        archive_failure = self.run_operation("archive-failure", "archive_failure", 1)
        self.assertEqual(archive_failure["status"], "failed")
        self.assertTrue(archive_failure["activated"])
        self.assertEqual(archive_failure["failure_phase"], "archive")

    def test_interruption_crash_reboot_and_lost_client(self):
        for operation_id, scenario, stop_signal, expected_initial in (
            ("interruption", "interrupt", signal.SIGTERM, 143),
            ("process-crash", "crash", signal.SIGKILL, -signal.SIGKILL),
            ("host-reboot", "reboot", signal.SIGKILL, -signal.SIGKILL),
        ):
            command = self.command(operation_id, scenario)
            process = subprocess.Popen(
                command,
                env={**os.environ, "UWA_DB_DEPLOY_TEST_MODE": "1"},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            state_path = self.state_root / operation_id / "state.json"
            for _ in range(200):
                marker = self.state_root / operation_id / "stage-waited"
                if (state_path.exists()
                    and json.loads(state_path.read_text()).get("current_phase") == "stage"
                    and marker.exists()):
                    break
                time.sleep(0.05)
            else:
                self.fail("operation did not enter stage")
            os.killpg(process.pid, stop_signal)
            self.assertEqual(process.wait(timeout=10), expected_initial)
            resumed = subprocess.run(
                command,
                env={**os.environ, "UWA_DB_DEPLOY_TEST_MODE": "1"},
                capture_output=True,
                text=True,
                timeout=150,
            )
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            state = json.loads(state_path.read_text())
            self.assertEqual(state["status"], "succeeded")
            self.assertGreaterEqual(state["resume_count"], 1)
            self.assertGreaterEqual(self.calls(operation_id).count("recover"), 2)

        lost = subprocess.Popen(
            self.command("lost-client", "success"),
            env={**os.environ, "UWA_DB_DEPLOY_TEST_MODE": "1"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.assertEqual(lost.wait(timeout=30), 0)
        state = json.loads((self.state_root / "lost-client" / "state.json").read_text())
        self.assertEqual(state["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
