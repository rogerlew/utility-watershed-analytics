#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_USER = "65532:65532"
EXPECTED_ENTRYPOINT = ["python3", "-m", "uwa_release_tool"]
PROHIBITED_PATH_PARTS = (
    "/.env",
    "/.git/",
    "/data-releases/",
    "/fixtures/",
    "/plans/",
    "/source-data/",
    "/app/server/",
    "/app/client/",
)
PROHIBITED_CONTENT = (
    b"AWS_SECRET_ACCESS_KEY=",
    b"B2_APPLICATION_KEY=",
    b"DJANGO_SECRET_KEY=",
    b"-----BEGIN PRIVATE KEY-----",
)


class ImageVerificationError(RuntimeError):
    pass


def run_command(arguments: list[str], *, expected_exit: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(arguments, text=True, capture_output=True, check=False)
    if completed.returncode != expected_exit:
        raise ImageVerificationError(
            f"command exit {completed.returncode}, expected {expected_exit}: {arguments[0]}"
        )
    return completed


def inspect_image(image: str) -> tuple[str, dict[str, Any]]:
    completed = run_command(["docker", "image", "inspect", image])
    documents = json.loads(completed.stdout)
    if len(documents) != 1:
        raise ImageVerificationError("docker inspect returned unexpected image count")
    document = documents[0]
    image_id = document["Id"]
    config = document["Config"]
    if config["User"] != EXPECTED_USER:
        raise ImageVerificationError(f"image user differs: {config['User']}")
    if config["Entrypoint"] != EXPECTED_ENTRYPOINT:
        raise ImageVerificationError(f"image entrypoint differs: {config['Entrypoint']}")
    sensitive_environment = [
        value
        for value in config.get("Env", [])
        if value.split("=", 1)[0]
        in {"AWS_SECRET_ACCESS_KEY", "B2_APPLICATION_KEY", "DJANGO_SECRET_KEY"}
    ]
    if sensitive_environment:
        raise ImageVerificationError("image configuration contains sensitive environment names")
    return image_id, document


def prohibited_member_names(names: list[str]) -> list[str]:
    normalized = ["/" + name.removeprefix("./").lstrip("/") for name in names]
    return sorted(
        name
        for name in normalized
        if any(part in name for part in PROHIBITED_PATH_PARTS)
        or name.endswith(("/release-manifest.json", "/forward.json", "/rollback.json"))
    )


def audit_export(image: str) -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="uwa-db11-image-") as temporary:
        container = run_command(["docker", "create", image]).stdout.strip()
        archive = Path(temporary) / "rootfs.tar"
        try:
            run_command(["docker", "export", "--output", str(archive), container])
        finally:
            run_command(["docker", "rm", container])

        with tarfile.open(archive, "r") as rootfs:
            members = rootfs.getmembers()
            names = [member.name for member in members]
            prohibited = prohibited_member_names(names)
            if prohibited:
                raise ImageVerificationError(f"prohibited image paths: {prohibited}")
            required = {
                "opt/release-tool/uwa_release_tool/__init__.py",
                "opt/release-tool/uwa_release_tool/__main__.py",
                "opt/release-tool/uwa_release_tool/artifacts.py",
                "opt/release-tool/uwa_release_tool/cli.py",
                "opt/release-tool/uwa_release_tool/enrichment.py",
                "opt/release-tool/uwa_release_tool/sources.py",
            }
            if not required.issubset(set(names)):
                raise ImageVerificationError("release-tool package is incomplete in image")
            scanned_files = 0
            for member in members:
                if not member.isfile() or not member.name.startswith("opt/release-tool/"):
                    continue
                extracted = rootfs.extractfile(member)
                if extracted is None:
                    continue
                content = extracted.read()
                scanned_files += 1
                if any(pattern in content for pattern in PROHIBITED_CONTENT):
                    raise ImageVerificationError(f"prohibited content in {member.name}")
    return {"rootfs_entries": len(names), "project_files_scanned": scanned_files}


def parse_events(output: str) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in output.splitlines() if line]
    except json.JSONDecodeError as error:
        raise ImageVerificationError("image emitted non-JSON output") from error


def verify_invocation(image_id: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="uwa-db11-input-") as temporary:
        root = Path(temporary)
        root.chmod(0o755)
        input_path = root / "release.json"
        content = b'{"release_id":"db11-image-fixture"}\n'
        input_path.write_bytes(content)
        input_path.chmod(0o444)
        digest = hashlib.sha256(content).hexdigest()
        mount = f"type=bind,src={input_path},dst=/inputs/release.json,readonly"
        base = [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--network",
            "none",
            "--mount",
            mount,
            image_id,
            "validate",
            "--input",
            "/inputs/release.json",
            "--require-read-only",
            "--sha256",
        ]
        accepted = run_command([*base, digest])
        accepted_events = parse_events(accepted.stdout)
        if accepted_events[-1].get("input_sha256") != digest:
            raise ImageVerificationError("digest-pinned invocation did not report expected SHA-256")
        rejected = run_command([*base, "0" * 64], expected_exit=11)
        rejected_events = parse_events(rejected.stderr)
        if rejected_events[-1].get("error_code") != "sha256_mismatch":
            raise ImageVerificationError("wrong-digest invocation was not distinguishable")
        if hashlib.sha256(input_path.read_bytes()).hexdigest() != digest:
            raise ImageVerificationError("read-only input changed during invocation")

    unavailable = run_command(
        ["docker", "run", "--rm", "--read-only", "--network", "none", image_id, "apply"],
        expected_exit=20,
    )
    unavailable_events = parse_events(unavailable.stderr)
    if unavailable_events[-1].get("error_code") != "command_unavailable":
        raise ImageVerificationError("future command did not fail as unavailable")
    artifact_import = run_command(
        [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--network",
            "none",
            "--entrypoint",
            "python3",
            image_id,
            "-c",
            "from uwa_release_tool.artifacts import validate_digest; print(validate_digest('0' * 64))",
        ]
    )
    if artifact_import.stdout.strip() != "0" * 64:
        raise ImageVerificationError("artifact client module import failed")
    source_import = run_command(
        [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--network",
            "none",
            "--entrypoint",
            "python3",
            image_id,
            "-c",
            "from uwa_release_tool.sources import canonical_json; print(canonical_json({'ok': True}).decode(), end='')",
        ]
    )
    if source_import.stdout.strip() != '{"ok":true}':
        raise ImageVerificationError("source preparation module import failed")
    enrichment_import = run_command(
        [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--network",
            "none",
            "--entrypoint",
            "python3",
            image_id,
            "-c",
            "from uwa_release_tool.enrichment import JOIN_KEY; print(JOIN_KEY)",
        ]
    )
    if enrichment_import.stdout.strip() != "WWS_Code":
        raise ImageVerificationError("NASA enrichment module import failed")
    return {
        "artifact_module_imported": True,
        "enrichment_module_imported": True,
        "source_module_imported": True,
        "input_sha256": digest,
        "wrong_digest_exit": 11,
        "unavailable_exit": 20,
    }


def verify_image(image: str) -> dict[str, Any]:
    image_id, document = inspect_image(image)
    audit = audit_export(image_id)
    invocation = verify_invocation(image_id)
    return {
        "status": "passed",
        "image_id": image_id,
        "architecture": document["Architecture"],
        "os": document["Os"],
        "user": document["Config"]["User"],
        **audit,
        **invocation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and execute the DB11 release-tool image.")
    parser.add_argument("--image", required=True)
    arguments = parser.parse_args()
    try:
        result = verify_image(arguments.image)
    except (ImageVerificationError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
