#!/usr/bin/env python3

import argparse
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


SHA256 = re.compile(r"^[a-f0-9]{64}$")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key)\s*[:=]\s*\S+"
)
URI_USERINFO = re.compile(r"https?://[^/@\s]+@", re.IGNORECASE)
FORBIDDEN_KEYS = {
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "credential",
    "credentials",
}
NONTERMINAL = {"pending", "running", "interrupted"}
FAILED = {"failed", "rollback_failed"}


class StatusError(RuntimeError):
    pass


def parse_time(value, name):
    if not isinstance(value, str):
        raise StatusError(f"Timestamp is invalid: {name}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise StatusError(f"Timestamp is invalid: {name}") from error
    if parsed.tzinfo is None:
        raise StatusError(f"Timestamp lacks timezone: {name}")
    return parsed.astimezone(timezone.utc)


def validate_public(value, path="document"):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS:
                raise StatusError(f"Secret-bearing key: {path}.{key}")
            validate_public(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_public(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if SECRET_ASSIGNMENT.search(value) or URI_USERINFO.search(value):
            raise StatusError(f"Secret-bearing value: {path}")


def read_json(path, *, private=False):
    try:
        details = path.lstat()
    except OSError as error:
        raise StatusError(f"Status input is unavailable: {path.name}") from error
    if not stat.S_ISREG(details.st_mode) or path.is_symlink():
        raise StatusError(f"Status input is not an ordinary file: {path.name}")
    if private and stat.S_IMODE(details.st_mode) & 0o077:
        raise StatusError(f"Private status file mode is too broad: {path.name}")
    if details.st_size > 10 * 1024 * 1024:
        raise StatusError(f"Status input exceeds bounded size: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StatusError(f"Status input is invalid JSON: {path.name}") from error
    if not isinstance(value, dict):
        raise StatusError(f"Status input must be a JSON object: {path.name}")
    validate_public(value, path.name)
    return value


def check(condition, code, summary):
    return {
        "code": code,
        "status": "passed" if condition else "failed",
        "summary": summary,
    }


def release_coordinates(document, name):
    if document.get("schema_version") != 1:
        raise StatusError(f"Schema version is unsupported: {name}")
    state = document.get("state")
    active = document.get("active_release")
    if state == "EMPTY" and active is None:
        return None
    if state != "ACTIVE" or not isinstance(active, dict):
        raise StatusError(f"Active release coordinates are incoherent: {name}")
    required = {"release_id", "manifest_sha256", "data_contract", "activated_at", "counts"}
    if set(active) != required or not SHA256.fullmatch(str(active["manifest_sha256"])):
        raise StatusError(f"Active release coordinates are invalid: {name}")
    counts = active["counts"]
    if not isinstance(counts, dict) or set(counts) != {
        "watersheds",
        "subcatchments",
        "channels",
        "capabilities",
    } or any(not isinstance(value, int) or value < 0 for value in counts.values()):
        raise StatusError(f"Active release counts are invalid: {name}")
    parse_time(active["activated_at"], f"{name}.activated_at")
    return {
        "release_id": active["release_id"],
        "manifest_sha256": active["manifest_sha256"],
        "counts": counts,
    }


def inventory_coordinates(document):
    if document.get("schema_version") != 1:
        raise StatusError("Inventory schema version is unsupported.")
    required = {
        "schema_version",
        "release_id",
        "manifest_sha256",
        "counts",
        "captured_at",
        "artifact_published_at",
    }
    if set(document) != required:
        raise StatusError("Inventory snapshot keys are invalid.")
    parse_time(document["captured_at"], "inventory.captured_at")
    parse_time(document["artifact_published_at"], "inventory.artifact_published_at")
    counts = document["counts"]
    if not isinstance(counts, dict) or set(counts) != {
        "watersheds",
        "subcatchments",
        "channels",
        "capabilities",
    } or any(not isinstance(value, int) or value < 0 for value in counts.values()):
        raise StatusError("Inventory counts are invalid.")
    if document["release_id"] is None:
        if document["manifest_sha256"] is not None or any(document["counts"].values()):
            raise StatusError("EMPTY inventory coordinates are incoherent.")
        return None
    if not SHA256.fullmatch(str(document["manifest_sha256"])):
        raise StatusError("Inventory manifest SHA-256 is invalid.")
    return {
        "release_id": document["release_id"],
        "manifest_sha256": document["manifest_sha256"],
        "counts": document["counts"],
    }


def atomic_report(path, document):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def evaluate(arguments):
    active_document = read_json(arguments.active_status)
    inventory = read_json(arguments.inventory_snapshot)
    storage = read_json(arguments.storage_snapshot, private=True)
    backup = read_json(arguments.backup_snapshot, private=True)
    now = parse_time(arguments.now, "now") if arguments.now else datetime.now(timezone.utc)
    active = release_coordinates(active_document, "active-status")
    expected = inventory_coordinates(inventory)
    checks = [
        check(active == expected, "active-inventory-match", "Active release matches the accepted inventory snapshot."),
    ]

    if storage.get("schema_version") != 1:
        raise StatusError("Storage snapshot schema version is unsupported.")
    for key in ("capacity_bytes", "available_bytes", "artifact_bytes", "previous_artifact_bytes"):
        if not isinstance(storage.get(key), int) or storage[key] < 0:
            raise StatusError(f"Storage value is invalid: {key}")
    parse_time(storage.get("observed_at"), "storage.observed_at")
    if storage["available_bytes"] > storage["capacity_bytes"]:
        raise StatusError("Available storage exceeds total capacity.")
    growth = storage["artifact_bytes"] - storage["previous_artifact_bytes"]
    checks.extend((
        check(
            storage["available_bytes"] >= arguments.minimum_available_bytes,
            "storage-capacity",
            "Artifact storage has the required available capacity.",
        ),
        check(
            growth <= arguments.maximum_growth_bytes,
            "storage-growth",
            "Artifact storage growth is within the reviewed bound.",
        ),
    ))
    artifact_age = now - parse_time(inventory["artifact_published_at"], "inventory.artifact_published_at")
    if artifact_age < timedelta(0):
        raise StatusError("Artifact publication timestamp is in the future.")
    checks.append(check(
        artifact_age <= timedelta(hours=arguments.maximum_artifact_age_hours),
        "artifact-age",
        "Accepted artifact publication is fresh.",
    ))

    if (
        backup.get("schema_version") != 1
        or not isinstance(backup.get("snapshot_id"), str)
        or not backup["snapshot_id"]
    ):
        raise StatusError("Backup snapshot is invalid.")
    backup_age = now - parse_time(backup.get("latest_completed_at"), "backup.latest_completed_at")
    if backup_age < timedelta(0):
        raise StatusError("Backup completion timestamp is in the future.")
    checks.append(check(
        backup_age <= timedelta(hours=arguments.maximum_backup_age_hours),
        "backup-age",
        "Verified database backup is fresh.",
    ))

    failed_attempts = 0
    abandoned_attempts = 0
    if arguments.attempt_root.is_symlink() or not arguments.attempt_root.is_dir():
        raise StatusError("Attempt root is not an ordinary directory.")
    for operation in arguments.attempt_root.iterdir():
        if not operation.is_dir() or operation.is_symlink():
            continue
        state_path = operation / "state.json"
        if not state_path.exists():
            continue
        state = read_json(state_path, private=True)
        status = state.get("status")
        if status in FAILED:
            failed_attempts += 1
        if status in NONTERMINAL:
            updated = parse_time(state.get("updated_at"), f"attempt.{operation.name}.updated_at")
            if now - updated > timedelta(hours=arguments.abandoned_attempt_hours):
                abandoned_attempts += 1
    checks.extend((
        check(failed_attempts == 0, "failed-attempts", "No unretired failed deployment attempt exists."),
        check(abandoned_attempts == 0, "abandoned-attempts", "No deployment attempt is abandoned."),
    ))
    status = "passed" if all(item["status"] == "passed" for item in checks) else "failed"
    report = {
        "schema_version": 1,
        "status": status,
        "observed_at": now.isoformat().replace("+00:00", "Z"),
        "active_release": active,
        "checks": checks,
        "metrics": {
            "available_bytes": storage["available_bytes"],
            "artifact_bytes": storage["artifact_bytes"],
            "artifact_growth_bytes": growth,
            "artifact_age_seconds": int(artifact_age.total_seconds()),
            "backup_age_seconds": int(backup_age.total_seconds()),
            "failed_attempts": failed_attempts,
            "abandoned_attempts": abandoned_attempts,
        },
    }
    atomic_report(arguments.report, report)
    print(json.dumps(report, sort_keys=True))
    return 0 if status == "passed" else 1


def parser():
    value = argparse.ArgumentParser(description="Evaluate private database release health snapshots.")
    value.add_argument("--active-status", type=Path, required=True)
    value.add_argument("--inventory-snapshot", type=Path, required=True)
    value.add_argument("--storage-snapshot", type=Path, required=True)
    value.add_argument("--backup-snapshot", type=Path, required=True)
    value.add_argument("--attempt-root", type=Path, required=True)
    value.add_argument("--report", type=Path, required=True)
    value.add_argument("--minimum-available-bytes", type=int, default=100 * 1024**3)
    value.add_argument("--maximum-growth-bytes", type=int, default=100 * 1024**3)
    value.add_argument("--maximum-artifact-age-hours", type=int, default=24 * 31)
    value.add_argument("--maximum-backup-age-hours", type=int, default=25)
    value.add_argument("--abandoned-attempt-hours", type=int, default=2)
    value.add_argument("--now")
    return value


def main():
    arguments = parser().parse_args()
    try:
        return evaluate(arguments)
    except StatusError as error:
        print(json.dumps({"status": "invalid", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
