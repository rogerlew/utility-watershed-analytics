#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path


SHA256 = re.compile(r"^[a-f0-9]{64}$")
GIT_COMMIT = re.compile(r"^[a-f0-9]{40}$")
STABLE_KEY = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]{0,94}[a-z0-9])?$")
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
FILES = {
    "request": "request.json",
    "release": "release.json",
    "members": "members.json",
    "forward_plan": "forward.json",
    "inverse_plan": "inverse.json",
    "clean_build_report": "clean-build-report.json",
    "inventory_snapshot": "inventory-snapshot.json",
}


class AuthorizationError(RuntimeError):
    pass


def canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode() + b"\n"


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ordinary_file(path, *, readonly=False):
    try:
        details = path.lstat()
    except OSError as error:
        raise AuthorizationError(f"Required file is unavailable: {path.name}") from error
    if not stat.S_ISREG(details.st_mode) or path.is_symlink():
        raise AuthorizationError(f"Required path is not an ordinary file: {path.name}")
    if readonly and stat.S_IMODE(details.st_mode) & 0o222:
        raise AuthorizationError(f"Bundle file is writable: {path.name}")
    if details.st_size > 20 * 1024 * 1024:
        raise AuthorizationError(f"Bundle file exceeds the bounded size: {path.name}")


def read_json(path):
    ordinary_file(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthorizationError(f"Invalid JSON file: {path.name}") from error
    if not isinstance(value, dict):
        raise AuthorizationError(f"JSON document must be an object: {path.name}")
    validate_public(value, path.name)
    return value


def validate_public(value, path="document"):
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS:
                raise AuthorizationError(f"Secret-bearing key: {path}.{key}")
            validate_public(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_public(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if SECRET_ASSIGNMENT.search(value) or URI_USERINFO.search(value):
            raise AuthorizationError(f"Secret-bearing value: {path}")


def validate_source_documents(documents, source_paths):
    request = documents["request"]
    if request.get("schema_version") != 1:
        raise AuthorizationError("Deployment request schema is unsupported.")
    operation_id = request.get("operation_id")
    release_id = request.get("release_id")
    if not STABLE_KEY.fullmatch(str(operation_id)):
        raise AuthorizationError("Operation ID is invalid.")
    if not isinstance(release_id, str) or not release_id:
        raise AuthorizationError("Release ID is invalid.")
    inputs = request.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "release",
        "members",
        "forward_plan",
        "inverse_plan",
    }:
        raise AuthorizationError("Deployment request input coordinates are incomplete.")
    for name in inputs:
        coordinate = inputs[name]
        if not isinstance(coordinate, dict) or set(coordinate) != {"path", "sha256"}:
            raise AuthorizationError(f"Request coordinate is invalid: {name}")
        if not SHA256.fullmatch(str(coordinate["sha256"])):
            raise AuthorizationError(f"Request SHA-256 is invalid: {name}")
        expected_path = (
            Path("/srv/utility-watershed-analytics/releases")
            / operation_id
            / FILES[name]
        )
        if Path(str(coordinate["path"])) != expected_path:
            raise AuthorizationError(f"Request deployed path is invalid: {name}")
        if digest_file(source_paths[name]) != coordinate["sha256"]:
            raise AuthorizationError(f"Request/source SHA-256 differs: {name}")
    release = documents["release"]
    if release.get("release_id") != release_id:
        raise AuthorizationError("Release document ID differs from the request.")
    manifest = release.get("manifest_sha256")
    if not SHA256.fullmatch(str(manifest)):
        raise AuthorizationError("Release manifest SHA-256 is invalid.")
    clean_build = documents["clean_build_report"]
    if clean_build.get("status") != "passed" or clean_build.get("release_id") != release_id:
        raise AuthorizationError("Clean-build report did not pass for the target release.")
    if clean_build.get("manifest_sha256") != manifest:
        raise AuthorizationError("Clean-build report manifest differs from the release.")
    inventory = documents["inventory_snapshot"]
    if inventory.get("schema_version") != 1 or inventory.get("release_id") != release_id:
        raise AuthorizationError("Inventory snapshot differs from the target release.")
    if inventory.get("manifest_sha256") != manifest:
        raise AuthorizationError("Inventory manifest differs from the release.")
    counts = inventory.get("counts")
    if not isinstance(counts, dict) or set(counts) != {
        "watersheds",
        "subcatchments",
        "channels",
        "capabilities",
    } or any(not isinstance(value, int) or value < 0 for value in counts.values()):
        raise AuthorizationError("Inventory counts are invalid.")
    return operation_id, release_id, manifest


def write_atomic(path, content, mode):
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare(arguments):
    if arguments.output.exists():
        raise AuthorizationError("Bundle output already exists.")
    source_paths = {name: Path(getattr(arguments, name)) for name in FILES}
    source_root = arguments.source_root.resolve()
    for name, path in source_paths.items():
        try:
            path.resolve().relative_to(source_root)
        except (OSError, ValueError) as error:
            raise AuthorizationError(f"Source path escapes the reviewed root: {name}") from error
    documents = {name: read_json(path) for name, path in source_paths.items()}
    operation_id, release_id, manifest = validate_source_documents(documents, source_paths)
    if not GIT_COMMIT.fullmatch(arguments.source_commit):
        raise AuthorizationError("Source commit is invalid.")
    if not STABLE_KEY.fullmatch(arguments.preparation_run_id):
        raise AuthorizationError("Preparation run ID is invalid.")
    arguments.output.mkdir(mode=0o700, parents=True)
    copied = {}
    try:
        for name, filename in FILES.items():
            destination = arguments.output / filename
            shutil.copyfile(source_paths[name], destination, follow_symlinks=False)
            destination.chmod(0o400)
            copied[name] = {
                "filename": filename,
                "sha256": digest_file(destination),
            }
        authorization = {
            "schema_version": 1,
            "action": arguments.action,
            "operation_id": operation_id,
            "release_id": release_id,
            "manifest_sha256": manifest,
            "source_commit": arguments.source_commit,
            "preparation_run_id": arguments.preparation_run_id,
            "files": copied,
        }
        content = canonical_bytes(authorization)
        authorization_path = arguments.output / "authorization.json"
        write_atomic(authorization_path, content, 0o400)
    except Exception:
        for path in arguments.output.iterdir():
            path.chmod(0o600)
            path.unlink()
        arguments.output.rmdir()
        raise
    result = {
        "status": "passed",
        "action": arguments.action,
        "operation_id": operation_id,
        "release_id": release_id,
        "authorization_sha256": digest_bytes(content),
        "bundle_files": len(copied) + 1,
    }
    print(json.dumps(result, sort_keys=True))


def verify(arguments):
    if arguments.bundle.is_symlink() or not arguments.bundle.is_dir():
        raise AuthorizationError("Bundle path is not an ordinary directory.")
    authorization_path = arguments.bundle / "authorization.json"
    ordinary_file(authorization_path, readonly=True)
    if not SHA256.fullmatch(arguments.authorization_sha256):
        raise AuthorizationError("Expected authorization SHA-256 is invalid.")
    if digest_file(authorization_path) != arguments.authorization_sha256:
        raise AuthorizationError("Authorization SHA-256 differs from protected input.")
    authorization = read_json(authorization_path)
    if authorization.get("schema_version") != 1:
        raise AuthorizationError("Authorization schema is unsupported.")
    if authorization.get("action") != arguments.action:
        raise AuthorizationError("Authorization action differs from the protected path.")
    if authorization.get("operation_id") != arguments.operation_id:
        raise AuthorizationError("Authorization operation differs from the protected input.")
    if arguments.source_commit and authorization.get("source_commit") != arguments.source_commit:
        raise AuthorizationError("Authorization source commit differs from checkout.")
    file_coordinates = authorization.get("files")
    if not isinstance(file_coordinates, dict) or set(file_coordinates) != set(FILES):
        raise AuthorizationError("Authorization file coordinates are incomplete.")
    expected_names = {"authorization.json", *FILES.values()}
    actual_names = {path.name for path in arguments.bundle.iterdir()}
    if actual_names != expected_names:
        raise AuthorizationError("Bundle members differ from authorization.")
    paths = {}
    for name, expected_filename in FILES.items():
        coordinate = file_coordinates[name]
        if not isinstance(coordinate, dict) or coordinate.get("filename") != expected_filename:
            raise AuthorizationError(f"Authorization filename differs: {name}")
        expected_digest = coordinate.get("sha256")
        if not SHA256.fullmatch(str(expected_digest)):
            raise AuthorizationError(f"Authorization digest is invalid: {name}")
        path = arguments.bundle / expected_filename
        ordinary_file(path, readonly=True)
        if digest_file(path) != expected_digest:
            raise AuthorizationError(f"Bundle file digest differs: {name}")
        paths[name] = path
    documents = {name: read_json(path) for name, path in paths.items()}
    operation_id, release_id, manifest = validate_source_documents(documents, paths)
    if authorization.get("release_id") != release_id or authorization.get("manifest_sha256") != manifest:
        raise AuthorizationError("Authorization release coordinates differ from bundle contents.")
    result = {
        "status": "passed",
        "action": arguments.action,
        "operation_id": operation_id,
        "release_id": release_id,
        "authorization_sha256": arguments.authorization_sha256,
        "request_sha256": file_coordinates["request"]["sha256"],
    }
    if arguments.result:
        arguments.result.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        write_atomic(arguments.result, canonical_bytes(result), 0o600)
    print(json.dumps(result, sort_keys=True))


def parser():
    root = argparse.ArgumentParser(description="Prepare or verify an immutable release authorization bundle.")
    commands = root.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--action", choices=("deploy", "rollback"), required=True)
    prepare_parser.add_argument("--source-commit", required=True)
    prepare_parser.add_argument("--preparation-run-id", required=True)
    prepare_parser.add_argument("--source-root", type=Path, default=Path.cwd())
    prepare_parser.add_argument("--output", type=Path, required=True)
    for name in FILES:
        prepare_parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--action", choices=("deploy", "rollback"), required=True)
    verify_parser.add_argument("--bundle", type=Path, required=True)
    verify_parser.add_argument("--authorization-sha256", required=True)
    verify_parser.add_argument("--operation-id", required=True)
    verify_parser.add_argument("--source-commit")
    verify_parser.add_argument("--result", type=Path)
    return root


def main():
    arguments = parser().parse_args()
    try:
        if arguments.command == "prepare":
            prepare(arguments)
        else:
            verify(arguments)
    except AuthorizationError as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
