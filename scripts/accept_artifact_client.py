#!/usr/bin/env python3

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "release-tool"))

from uwa_release_tool import artifacts  # noqa: E402


DEFAULT_WORKSPACE = Path("/wc1/utility-watershed-analytics-artifacts/v1/test")


class AcceptanceError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def run_acceptance(workspace: Path) -> dict[str, Any]:
    if not workspace.is_dir():
        raise AcceptanceError("accepted test workspace does not exist")

    acceptance_path: Path | None = None
    result: dict[str, Any]
    with tempfile.TemporaryDirectory(prefix=".db12-acceptance-", dir=workspace) as temporary:
        acceptance_path = Path(temporary)
        acceptance_path.chmod(0o700)
        store = acceptance_path / "test-store"
        production_store = acceptance_path / "production-store"
        cache = acceptance_path / "cache"
        store.mkdir(mode=0o700)
        production_store.mkdir(mode=0o700)
        client = artifacts.ArtifactClient(store, cache, chunk_size=4096)

        source = acceptance_path / "source.bin"
        content = (b"DB12-forest1-streaming-fixture\n" * 65536)[: 2 * 1024 * 1024]
        source.write_bytes(content)
        expected_digest = hashlib.sha256(content).hexdigest()
        published = client.publish(source, expected_sha256=expected_digest)
        fetched = client.fetch(published.digest)
        require(fetched.path.read_bytes() == content, "initial fetch differs")

        fetched.path.write_bytes(b"corrupt")
        recovered = client.fetch(published.digest)
        require(recovered.recovered_corruption, "corrupt cache was not recovered")
        require(recovered.path.read_bytes() == content, "recovered cache differs")

        recovered.path.unlink()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            concurrent_results = list(
                executor.map(lambda _: client.fetch(published.digest), range(16))
            )
        require(
            all(item.path.read_bytes() == content for item in concurrent_results),
            "concurrent fetch differs",
        )

        try:
            client.fetch("0" * 64)
        except artifacts.ArtifactNotFound:
            missing_object_rejected = True
        else:
            missing_object_rejected = False

        try:
            client.publish(source, expected_sha256="0" * 64)
        except artifacts.ArtifactIntegrityError:
            wrong_checksum_rejected = True
        else:
            wrong_checksum_rejected = False

        def interrupt(operation: str, _byte_count: int) -> None:
            if operation == "fetch":
                raise RuntimeError("injected interruption")

        interrupted_cache = acceptance_path / "interrupted-cache"
        interrupted_client = artifacts.ArtifactClient(
            store,
            interrupted_cache,
            chunk_size=4096,
            progress=interrupt,
        )
        try:
            interrupted_client.fetch(published.digest)
        except artifacts.ArtifactTransferError:
            interrupted_fetch_rejected = True
        else:
            interrupted_fetch_rejected = False
        require(
            not interrupted_client.cache_path(published.digest).exists(),
            "interrupted fetch promoted cache bytes",
        )

        concurrent_results[0].path.unlink()
        published.path.chmod(0)
        try:
            try:
                client.fetch(published.digest)
            except artifacts.ArtifactPermissionError:
                permission_denied = True
            else:
                permission_denied = False
        finally:
            published.path.chmod(0o600)

        production = artifacts.ArtifactClient(production_store, acceptance_path / "prod-cache")
        try:
            production.fetch(published.digest)
        except artifacts.ArtifactNotFound:
            namespace_isolated = True
        else:
            namespace_isolated = False

        conflict_store = acceptance_path / "conflict-store"
        conflict_store.mkdir(mode=0o700)
        conflict = artifacts.ArtifactClient(conflict_store, acceptance_path / "conflict-cache")
        conflict_path = conflict.object_path(published.digest)
        conflict_path.parent.mkdir(parents=True, mode=0o700)
        conflict_path.write_bytes(b"different")
        try:
            conflict.publish(source)
        except artifacts.ArtifactConflictError:
            conflict_rejected = True
        else:
            conflict_rejected = False

        cleanup_records = []
        for index in range(3):
            cleanup_source = acceptance_path / f"cleanup-{index}.bin"
            cleanup_source.write_bytes(f"cleanup-{index}".encode())
            cleanup_records.append(client.publish(cleanup_source))
        for index, record in enumerate(cleanup_records):
            cached_path = client.fetch(record.digest).path
            os.utime(cached_path, ns=(index + 1, index + 1))
        cleanup = client.cleanup_cache(
            retained_digests=[published.digest, cleanup_records[0].digest],
            leased_digests=[cleanup_records[1].digest],
            max_entries=1,
            max_bytes=1024,
        )
        require(cleanup.digests == (cleanup_records[2].digest,), "cleanup selection differs")
        require(client.object_path(cleanup_records[2].digest).exists(), "cleanup touched store")

        checks = {
            "conflict_rejected": conflict_rejected,
            "corrupt_cache_recovered": recovered.recovered_corruption,
            "interrupted_fetch_rejected": interrupted_fetch_rejected,
            "missing_object_rejected": missing_object_rejected,
            "namespace_isolated": namespace_isolated,
            "permission_denied": permission_denied,
            "store_delete_api_absent": not hasattr(client, "delete"),
            "wrong_checksum_rejected": wrong_checksum_rejected,
        }
        require(all(checks.values()), f"acceptance check failed: {checks}")

        result = {
            "status": "passed",
            "workspace": str(workspace),
            "fixture_sha256": published.digest,
            "fixture_bytes": published.byte_count,
            "concurrent_fetches": len(concurrent_results),
            "cleanup_entries": cleanup.entry_count,
            "checks": checks,
        }

    require(acceptance_path is not None and not acceptance_path.exists(), "temporary subtree remains")
    result["temporary_subtree_removed"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Accept the DB12 client on forest1 storage.")
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    arguments = parser.parse_args()
    try:
        result = run_acceptance(arguments.workspace)
    except (AcceptanceError, artifacts.ArtifactError, OSError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
