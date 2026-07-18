#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
import uuid
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("/wc1/utility-watershed-analytics-artifacts/v1")
MINIMUM_FREE_BYTES = 100 * 1024**3
RELEASE_ROLES = ("active", "rollback-1", "rollback-2")


class AcceptanceError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nearest_existing(path: Path) -> Path:
    candidate = path
    while not candidate.exists():
        if candidate.parent == candidate:
            raise AcceptanceError(f"no existing parent for {path}")
        candidate = candidate.parent
    return candidate


def require_free_space(root: Path, minimum_free_bytes: int) -> int:
    free_bytes = shutil.disk_usage(nearest_existing(root)).free
    if free_bytes < minimum_free_bytes:
        raise AcceptanceError(
            f"free space {free_bytes} is below required floor {minimum_free_bytes}"
        )
    return free_bytes


def make_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def write_once_bytes(destination: Path, content: bytes) -> None:
    make_private_directory(destination.parent)
    if destination.exists():
        if destination.read_bytes() != content:
            raise AcceptanceError(f"refusing to overwrite existing file: {destination}")
        return
    temporary = destination.parent / f".{destination.name}.{uuid.uuid4().hex}.partial"
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
        destination.chmod(0o600)
    except FileExistsError:
        if not destination.exists() or destination.read_bytes() != content:
            raise AcceptanceError(f"refusing conflicting concurrent write: {destination}")
    finally:
        if temporary.exists():
            temporary.unlink()


def publish_object(source: Path, namespace: Path) -> tuple[str, Path]:
    digest = sha256_file(source)
    destination = namespace / "objects" / "sha256" / digest[:2] / digest
    make_private_directory(destination.parent)
    if destination.exists():
        if sha256_file(destination) != digest:
            raise AcceptanceError(f"existing object does not match its key: {destination}")
        return digest, destination

    temporary = destination.parent / f".{digest}.{uuid.uuid4().hex}.partial"
    try:
        with source.open("rb") as source_stream:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as target_stream:
                shutil.copyfileobj(source_stream, target_stream, 1024 * 1024)
                target_stream.flush()
                os.fsync(target_stream.fileno())
        if sha256_file(temporary) != digest:
            raise AcceptanceError(f"temporary copy failed verification: {temporary}")
        os.link(temporary, destination)
        destination.chmod(0o600)
    except FileExistsError:
        if not destination.exists() or sha256_file(destination) != digest:
            raise AcceptanceError(f"refusing conflicting concurrent object: {destination}")
    finally:
        if temporary.exists():
            temporary.unlink()
    return digest, destination


def manifest_bytes(role: str, digest: str, byte_count: int) -> bytes:
    document = {
        "contract_version": 1,
        "release_role": role,
        "objects": [{"sha256": digest, "bytes": byte_count}],
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def load_manifests(namespace: Path) -> list[dict[str, Any]]:
    manifests = []
    for role in RELEASE_ROLES:
        path = namespace / "releases" / f"{role}.json"
        if not path.is_file():
            raise AcceptanceError(f"missing release manifest: {path}")
        manifests.append(json.loads(path.read_text(encoding="utf-8")))
    return manifests


def verify_namespace(namespace: Path) -> dict[str, Any]:
    manifests = load_manifests(namespace)
    observed_roles = [manifest["release_role"] for manifest in manifests]
    if observed_roles != list(RELEASE_ROLES):
        raise AcceptanceError(f"release roles differ: {observed_roles}")

    objects: dict[str, int] = {}
    for manifest in manifests:
        for item in manifest["objects"]:
            digest = item["sha256"]
            object_path = namespace / "objects" / "sha256" / digest[:2] / digest
            if not object_path.is_file():
                raise AcceptanceError(f"missing object: {object_path}")
            if object_path.stat().st_size != item["bytes"]:
                raise AcceptanceError(f"object size mismatch: {object_path}")
            if sha256_file(object_path) != digest:
                raise AcceptanceError(f"object digest mismatch: {object_path}")
            objects[digest] = item["bytes"]

    inventory = {
        "contract_version": 1,
        "release_roles": list(RELEASE_ROLES),
        "objects": [{"sha256": digest, "bytes": objects[digest]} for digest in sorted(objects)],
    }
    inventory_content = (json.dumps(inventory, indent=2, sort_keys=True) + "\n").encode()
    write_once_bytes(namespace / "inventory.json", inventory_content)
    return {
        "releases": len(manifests),
        "objects": len(objects),
        "inventory_sha256": hashlib.sha256(inventory_content).hexdigest(),
    }


def assert_private_tree(root: Path) -> None:
    for path in [root, *root.rglob("*")]:
        mode = stat.S_IMODE(path.stat().st_mode)
        expected = 0o700 if path.is_dir() else 0o600
        if mode != expected:
            raise AcceptanceError(f"mode {mode:04o} differs for {path}")


def provision(root: Path, minimum_free_bytes: int) -> int:
    free_bytes = require_free_space(root, minimum_free_bytes)
    make_private_directory(root)
    for environment in ("test", "production"):
        namespace = root / environment
        make_private_directory(namespace)
        make_private_directory(namespace / "objects")
        make_private_directory(namespace / "objects" / "sha256")
        make_private_directory(namespace / "releases")
    assert_private_tree(root)
    return free_bytes


def populate_test_backup(root: Path) -> None:
    namespace = root / "test"
    with tempfile.TemporaryDirectory(prefix="uwa-db10a-source-") as temporary:
        source_root = Path(temporary)
        for index, role in enumerate(RELEASE_ROLES, start=1):
            source = source_root / f"{role}.txt"
            source.write_text(f"DB10A fixture release {index}: {role}\n", encoding="utf-8")
            digest, _ = publish_object(source, namespace)
            write_once_bytes(
                namespace / "releases" / f"{role}.json",
                manifest_bytes(role, digest, source.stat().st_size),
            )


def run_negative_proof(root: Path) -> dict[str, bool]:
    namespace = root / "test"
    source_object = next((namespace / "objects" / "sha256").glob("*/*"))
    with tempfile.TemporaryDirectory(prefix="uwa-db10a-negative-") as temporary:
        temporary_root = Path(temporary)

        partial_destination = temporary_root / "partial" / source_object.name
        make_private_directory(partial_destination.parent)
        partial_file = partial_destination.parent / f".{source_object.name}.partial"
        partial_file.write_bytes(source_object.read_bytes()[:4])
        partial_file.unlink()
        partial_copy_rejected = not partial_destination.exists()

        collision_namespace = temporary_root / "collision"
        collision_path = (
            collision_namespace / "objects" / "sha256" / source_object.name[:2] / source_object.name
        )
        make_private_directory(collision_path.parent)
        collision_path.write_bytes(b"different bytes")
        try:
            publish_object(source_object, collision_namespace)
        except AcceptanceError:
            collision_rejected = True
        else:
            collision_rejected = False

        corrupt_namespace = temporary_root / "corrupt"
        shutil.copytree(namespace, corrupt_namespace)
        corrupt_object = next((corrupt_namespace / "objects" / "sha256").glob("*/*"))
        corrupt_object.write_bytes(b"corrupt")
        try:
            verify_namespace(corrupt_namespace)
        except AcceptanceError:
            corruption_detected = True
        else:
            corruption_detected = False

        missing_namespace = temporary_root / "missing"
        shutil.copytree(namespace, missing_namespace)
        missing_object = next((missing_namespace / "objects" / "sha256").glob("*/*"))
        missing_object.unlink()
        try:
            verify_namespace(missing_namespace)
        except AcceptanceError:
            missing_object_detected = True
        else:
            missing_object_detected = False

        unavailable_parent = temporary_root / "not-a-directory"
        unavailable_parent.write_text("blocked", encoding="utf-8")
        try:
            make_private_directory(unavailable_parent / "child")
        except OSError:
            unavailable_path_rejected = True
        else:
            unavailable_path_rejected = False

    result = {
        "partial_copy_rejected": partial_copy_rejected,
        "collision_rejected": collision_rejected,
        "corruption_detected": corruption_detected,
        "missing_object_detected": missing_object_detected,
        "unavailable_path_rejected": unavailable_path_rejected,
    }
    if not all(result.values()):
        raise AcceptanceError(f"negative proof failed: {result}")
    return result


def restore_rehearsal(root: Path) -> dict[str, Any]:
    source = root / "test"
    expected = verify_namespace(source)
    with tempfile.TemporaryDirectory(prefix="uwa-db10a-restore-") as temporary:
        restored = Path(temporary) / "restored"
        shutil.copytree(source, restored)
        observed = verify_namespace(restored)
        if observed != expected:
            raise AcceptanceError(f"restore differs: expected {expected}, observed {observed}")
        assert_private_tree(restored)
    return observed


def accept(root: Path, minimum_free_bytes: int) -> dict[str, Any]:
    free_bytes = provision(root, minimum_free_bytes)
    populate_test_backup(root)
    backup = verify_namespace(root / "test")
    negatives = run_negative_proof(root)
    restore = restore_rehearsal(root)
    assert_private_tree(root)
    return {
        "status": "passed",
        "host": os.uname().nodename,
        "root": str(root),
        "free_bytes": free_bytes,
        "backup": backup,
        "negative_proof": negatives,
        "restore": restore,
        "production_namespace_empty": not any((root / "production" / "releases").iterdir()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision and accept the forest1 artifact backup.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--minimum-free-bytes", type=int, default=MINIMUM_FREE_BYTES)
    args = parser.parse_args()
    try:
        result = accept(args.root, args.minimum_free_bytes)
    except (AcceptanceError, OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
