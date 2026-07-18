#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


TERMINAL_STATUSES = {
    "succeeded",
    "noop",
    "failed",
    "rolled_back",
    "rollback_failed",
}
SHA256 = re.compile(r"^[a-f0-9]{64}$")
IMAGE = re.compile(r"^.+@sha256:[a-f0-9]{64}$")
IMAGE_ID = re.compile(r"^sha256:[a-f0-9]{64}$")
GIT_COMMIT = re.compile(r"^[a-f0-9]{40}$")
OPERATION_ID = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]{0,62}[a-z0-9])?$")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key)\s*[:=]\s*\S+"
)
URI_USERINFO = re.compile(r"(https?://)[^/@\s]+@", re.IGNORECASE)
FORBIDDEN_KEYS = {"password", "passwd", "token", "secret", "api_key", "apikey", "credentials"}


class DeploymentError(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sanitize(value):
    text = URI_USERINFO.sub(r"\1[REDACTED]@", str(value))
    text = SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
    text = " ".join(text.replace("\x00", " ").split())
    return text[:512]


def validate_public(value, path="result"):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS:
                raise DeploymentError(f"Secret-bearing adapter result key: {path}.{key}")
            validate_public(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_public(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if SECRET_ASSIGNMENT.search(value) or URI_USERINFO.search(value):
            raise DeploymentError(f"Secret-bearing adapter result value: {path}")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def ordinary_file(path, *, private=False, readonly=False):
    try:
        details = path.lstat()
    except OSError as error:
        raise DeploymentError(f"Required file is unavailable: {path}") from error
    if not stat.S_ISREG(details.st_mode) or path.is_symlink():
        raise DeploymentError(f"Required path is not an ordinary file: {path}")
    if details.st_uid != os.geteuid():
        raise DeploymentError(f"File owner differs from deployment principal: {path}")
    if private and stat.S_IMODE(details.st_mode) != 0o600:
        raise DeploymentError(f"Secret file mode must be 0600: {path}")
    if readonly and stat.S_IMODE(details.st_mode) & 0o222:
        raise DeploymentError(f"Reviewed input is writable: {path}")
    return details


def validate_request(path, expected_sha):
    ordinary_file(path, readonly=True)
    if not SHA256.fullmatch(expected_sha) or sha256(path) != expected_sha:
        raise DeploymentError("Deployment request SHA-256 differs from approval.")
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DeploymentError("Deployment request is not valid UTF-8 JSON.") from error
    if not isinstance(request, dict) or request.get("schema_version") != 1:
        raise DeploymentError("Deployment request schema version is unsupported.")
    required = {
        "schema_version",
        "operation_id",
        "release_id",
        "expected_base_manifest",
        "tool_image",
        "tool_image_id",
        "application_git_commit",
        "materializer_git_commit",
        "inputs",
    }
    if set(request) != required:
        raise DeploymentError("Deployment request keys differ from the version-1 contract.")
    if not OPERATION_ID.fullmatch(str(request["operation_id"])):
        raise DeploymentError("Operation ID is invalid.")
    if not isinstance(request["release_id"], str) or not request["release_id"]:
        raise DeploymentError("Release ID is invalid.")
    base = request["expected_base_manifest"]
    if base != "EMPTY" and not SHA256.fullmatch(str(base)):
        raise DeploymentError("Expected base manifest is invalid.")
    if not IMAGE.fullmatch(str(request["tool_image"])):
        raise DeploymentError("Tool image is not pinned by repository digest.")
    if not IMAGE_ID.fullmatch(str(request["tool_image_id"])):
        raise DeploymentError("Tool image ID is invalid.")
    for key in ("application_git_commit", "materializer_git_commit"):
        if not GIT_COMMIT.fullmatch(str(request[key])):
            raise DeploymentError(f"{key} is invalid.")
    inputs = request["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != {
        "release",
        "members",
        "forward_plan",
        "inverse_plan",
    }:
        raise DeploymentError("Reviewed input coordinates are incomplete.")
    for name, coordinates in inputs.items():
        if not isinstance(coordinates, dict) or set(coordinates) != {"path", "sha256"}:
            raise DeploymentError(f"Reviewed {name} coordinates are invalid.")
        input_path = Path(coordinates["path"])
        if not input_path.is_absolute() or not SHA256.fullmatch(str(coordinates["sha256"])):
            raise DeploymentError(f"Reviewed {name} coordinates are invalid.")
        ordinary_file(input_path, readonly=True)
        if sha256(input_path) != coordinates["sha256"]:
            raise DeploymentError(f"Reviewed {name} SHA-256 differs from approval.")
    return request


class Runner:
    def __init__(self, arguments, request, request_sha):
        self.arguments = arguments
        self.request = request
        self.request_sha = request_sha
        self.operation_dir = arguments.state_root / request["operation_id"]
        self.state_path = self.operation_dir / "state.json"
        self.report_path = self.operation_dir / "report.json"
        self.log_path = self.operation_dir / "deployment.log"
        self.results_dir = self.operation_dir / "results"
        self.child = None
        self.state = self.load_state()

    def coordinates(self):
        return {
            "request_sha256": self.request_sha,
            "release_id": self.request["release_id"],
            "expected_base_manifest": self.request["expected_base_manifest"],
            "tool_image": self.request["tool_image"],
            "tool_image_id": self.request["tool_image_id"],
            "inputs": {
                name: value["sha256"] for name, value in sorted(self.request["inputs"].items())
            },
        }

    def load_state(self):
        self.operation_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.operation_dir, 0o700)
        self.results_dir.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.results_dir, 0o700)
        if self.state_path.exists():
            ordinary_file(self.state_path, private=True)
            try:
                state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise DeploymentError("Durable deployment state is unreadable.") from error
            if state.get("coordinates") != self.coordinates():
                raise DeploymentError("Resume coordinates differ from durable state.")
            if state.get("status") in TERMINAL_STATUSES:
                raise DeploymentError(f"Operation is already terminal: {state['status']}")
            state["resume_count"] = int(state.get("resume_count", 0)) + 1
            return state
        return {
            "schema_version": 1,
            "operation_id": self.request["operation_id"],
            "coordinates": self.coordinates(),
            "status": "pending",
            "created_at": now(),
            "updated_at": now(),
            "completed_phases": [],
            "phase_results": {},
            "resume_count": 0,
            "activated": False,
            "rollback_attempted": False,
        }

    def save(self):
        self.state["updated_at"] = now()
        atomic_json(self.state_path, self.state)

    def log(self, level, message):
        line = f"{now()} {level} {sanitize(message)}\n"
        descriptor = os.open(self.log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(descriptor, line.encode())
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        print(line, end="", file=sys.stderr)

    def assert_lock(self):
        lock_fd = os.environ.get("UWA_OPERATION_LOCK_FD", "")
        pass_fds = (int(lock_fd),) if lock_fd.isdigit() else ()
        subprocess.run(
            [str(self.arguments.require_lock), "exclusive"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            pass_fds=pass_fds,
        )

    def invoke(self, phase, *, repeat=False, best_effort=False):
        if not repeat and phase in self.state["completed_phases"]:
            return self.state["phase_results"][phase]
        if phase in {"backup", "publish", "apply", "rollback"}:
            self.assert_lock()
        self.state["status"] = "running"
        self.state["current_phase"] = phase
        self.save()
        command = [
            str(self.arguments.adapter),
            phase,
            str(self.arguments.request),
            str(self.state_path),
            str(self.operation_dir),
            str(self.arguments.secret_file),
        ]
        environment = os.environ.copy()
        environment["UWA_DB_DEPLOY_REPORT_ARCHIVE"] = str(self.arguments.report_archive)
        environment["UWA_DB_DEPLOY_REPORT_RETENTION_DAYS"] = str(self.arguments.retention_days)
        try:
            self.child = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=environment,
            )
            stdout, stderr = self.child.communicate(timeout=self.arguments.phase_timeout)
            return_code = self.child.returncode
        except subprocess.TimeoutExpired:
            self.child.terminate()
            stdout, stderr = self.child.communicate(timeout=30)
            return_code = 124
        finally:
            self.child = None
        if stderr:
            self.log("ADAPTER", stderr)
        if return_code != 0:
            error = DeploymentError(f"Phase {phase} failed with exit {return_code}.")
            if best_effort:
                self.log("WARNING", error)
                return {"status": "failed"}
            raise error
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError as error:
            if best_effort:
                self.log("WARNING", f"Phase {phase} returned invalid JSON.")
                return {"status": "failed"}
            raise DeploymentError(f"Phase {phase} returned invalid JSON.") from error
        if not isinstance(result, dict) or result.get("status") != "passed":
            if best_effort:
                self.log("WARNING", f"Phase {phase} did not return passed status.")
                return {"status": "failed"}
            raise DeploymentError(f"Phase {phase} did not return passed status.")
        validate_public(result)
        result_path = self.results_dir / f"{phase}.json"
        atomic_json(result_path, result)
        if not repeat:
            self.state["phase_results"][phase] = result
            self.state["completed_phases"].append(phase)
        self.state.pop("current_phase", None)
        self.save()
        return result

    def alert(self, reason):
        prior_status = self.state.get("status")
        self.state["alert_reason"] = sanitize(reason)
        self.save()
        self.invoke("alert", repeat=True, best_effort=True)
        self.state["status"] = prior_status
        self.state.pop("current_phase", None)
        self.save()

    def report(self, status):
        report = {
            "schema_version": 1,
            "operation_id": self.state["operation_id"],
            "release_id": self.request["release_id"],
            "status": status,
            "coordinates": self.state["coordinates"],
            "completed_phases": self.state["completed_phases"],
            "phase_results": self.state["phase_results"],
            "activated": self.state["activated"],
            "rollback_attempted": self.state["rollback_attempted"],
            "created_at": self.state["created_at"],
            "completed_at": now(),
        }
        if "failure_phase" in self.state:
            report["failure_phase"] = self.state["failure_phase"]
            report["failure_summary"] = self.state["failure_summary"]
        atomic_json(self.report_path, report)
        self.state["report_sha256"] = sha256(self.report_path)
        self.save()

    def terminal(self, status):
        self.state["status"] = status
        self.state["completed_at"] = now()
        self.state.pop("current_phase", None)
        self.save()
        self.report(status)
        archive = self.invoke("archive", repeat=True, best_effort=True)
        if archive.get("status") != "passed":
            self.state["failure_phase"] = "archive"
            self.state["failure_summary"] = "Required off-host report archive failed."
            if status in {"succeeded", "noop"}:
                status = "failed"
        self.invoke("cleanup", repeat=True, best_effort=True)
        self.prune_terminal_state()
        self.state["status"] = status
        self.save()
        self.report(status)
        return status

    def prune_terminal_state(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.arguments.retention_days)
        for candidate in self.arguments.state_root.iterdir():
            if candidate == self.operation_dir or not candidate.is_dir() or candidate.is_symlink():
                continue
            candidate_state = candidate / "state.json"
            try:
                ordinary_file(candidate_state, private=True)
                document = json.loads(candidate_state.read_text(encoding="utf-8"))
                completed = datetime.fromisoformat(document["completed_at"].replace("Z", "+00:00"))
            except (DeploymentError, OSError, KeyError, ValueError, json.JSONDecodeError):
                continue
            if document.get("status") in TERMINAL_STATUSES and completed < cutoff:
                shutil.rmtree(candidate)

    def fail(self, error):
        phase = self.state.get("current_phase", "orchestrator")
        self.state["failure_phase"] = phase
        self.state["failure_summary"] = sanitize(error)
        if phase in {"smoke", "refresh"} and self.state["activated"]:
            try:
                self.state["rollback_attempted"] = True
                self.save()
                self.invoke("rollback")
                self.invoke("rollback_smoke")
                self.invoke("refresh", repeat=True)
                self.terminal("rolled_back")
                self.alert(f"Deployment failed in {phase}; exact rollback passed.")
                return 2
            except Exception as rollback_error:
                self.state["failure_summary"] = sanitize(rollback_error)
                self.terminal("rollback_failed")
                self.alert("Deployment and exact rollback failed.")
                return 3
        self.terminal("failed")
        self.alert(f"Deployment failed in {phase}.")
        return 1

    def run(self):
        self.save()
        self.log("INFO", f"Starting operation {self.state['operation_id']}.")
        if self.state["resume_count"] and self.state.get("status") in {"running", "interrupted"}:
            self.alert("Resuming a nonterminal deployment attempt.")
        self.invoke("recover", repeat=True)
        self.invoke("preflight")
        classification = self.invoke("classify")
        outcome = classification.get("outcome")
        if outcome == "noop":
            self.invoke("smoke")
            self.invoke("report")
            terminal_status = self.terminal("noop")
            self.log("INFO", "Verified active no-op completed without backup or activation.")
            return 0 if terminal_status == "noop" else 1
        if outcome != "apply":
            raise DeploymentError("Classification outcome is invalid.")
        for phase in ("prepare", "stage", "compatibility", "backup", "publish"):
            self.invoke(phase)
        backup = self.state["phase_results"]["backup"]
        publication = self.state["phase_results"]["publish"]
        if not SHA256.fullmatch(str(backup.get("backup_sha256", ""))):
            raise DeploymentError("Backup phase did not return a verified SHA-256.")
        if publication.get("verified") is not True:
            raise DeploymentError("Off-host backup publication is not verified.")
        apply = self.invoke("apply")
        if apply.get("activated") is not True:
            raise DeploymentError("Apply phase did not confirm activation.")
        self.state["activated"] = True
        self.save()
        self.invoke("smoke")
        self.invoke("refresh")
        self.invoke("report")
        terminal_status = self.terminal("succeeded")
        self.log("INFO", "Database deployment completed.")
        return 0 if terminal_status == "succeeded" else 1

    def interrupt(self, signum, _frame):
        if self.child is not None:
            try:
                self.child.terminate()
            except ProcessLookupError:
                pass
        self.state["status"] = "interrupted"
        self.state["interrupted_by"] = signal.Signals(signum).name
        self.save()
        self.log("WARNING", f"Operation interrupted by {signal.Signals(signum).name}; explicit resume required.")
        raise SystemExit(143 if signum != signal.SIGINT else 130)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Run one durable database deployment.")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--secret-file", required=True, type=Path)
    parser.add_argument("--state-root", type=Path, default=Path("/var/lib/utility-watershed-analytics/database-deployments"))
    parser.add_argument("--report-archive", default="forest1:/wc1/utility-watershed-analytics-db-deployment-reports")
    parser.add_argument("--retention-days", type=int, default=180)
    parser.add_argument("--phase-timeout", type=int, default=21600)
    parser.add_argument("--adapter", type=Path, default=Path(__file__).with_name("database_deployment_phase.sh"))
    parser.add_argument("--require-lock", type=Path, default=Path(__file__).with_name("require_operation_lock.sh"))
    arguments = parser.parse_args()
    if arguments.retention_days < 1 or arguments.phase_timeout < 1:
        parser.error("retention and timeout must be positive")
    for name in ("request", "secret_file", "adapter", "require_lock"):
        value = getattr(arguments, name)
        if not value.is_absolute():
            setattr(arguments, name, value.resolve())
    if not arguments.state_root.is_absolute():
        parser.error("--state-root must be absolute")
    if not (
        arguments.report_archive.startswith("/")
        or arguments.report_archive.startswith(
            "forest1:/wc1/utility-watershed-analytics-db-deployment-reports"
        )
    ):
        parser.error("--report-archive must use the accepted forest1:/wc1 root")
    return arguments


def main():
    arguments = parse_arguments()
    ordinary_file(arguments.secret_file, private=True)
    ordinary_file(arguments.adapter)
    default_adapter = Path(__file__).with_name("database_deployment_phase.sh").resolve()
    if arguments.adapter.resolve() != default_adapter and os.environ.get("UWA_DB_DEPLOY_TEST_MODE") != "1":
        raise DeploymentError("A custom phase adapter is allowed only in explicit test mode.")
    request = validate_request(arguments.request, arguments.request_sha256)
    runner = Runner(arguments, request, arguments.request_sha256)
    signal.signal(signal.SIGTERM, runner.interrupt)
    signal.signal(signal.SIGHUP, runner.interrupt)
    signal.signal(signal.SIGINT, runner.interrupt)
    try:
        return runner.run()
    except DeploymentError as error:
        runner.log("ERROR", error)
        return runner.fail(error)
    except Exception as error:
        runner.log("ERROR", type(error).__name__)
        return runner.fail(DeploymentError(type(error).__name__))


if __name__ == "__main__":
    sys.exit(main())
