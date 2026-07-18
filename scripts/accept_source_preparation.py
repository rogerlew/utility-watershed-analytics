#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "release-tool"))

from uwa_release_tool import artifacts, sources  # noqa: E402


ACCEPTED_TEST_NAMESPACE = Path("/wc1/utility-watershed-analytics-artifacts/v1/test")
ARTIFACT_BASE = "https://artifacts.example.test/db17-acceptance"
MASTER_URL = "https://source.example.test/resources/custom-db17-master.geojson"


def feature(runid: str) -> dict:
    return {
        "type": "Feature",
        "properties": {"runid": runid, "source_label": "db17-acceptance"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[-117.0, 46.0], [-116.9, 46.0], [-116.9, 46.1], [-117.0, 46.0]]
            ],
        },
    }


def geojson(runid: str) -> bytes:
    return sources.canonical_json({"type": "FeatureCollection", "features": [feature(runid)]})


def parquet() -> bytes:
    metadata = b"db17-acceptance"
    return b"PAR1" + metadata + len(metadata).to_bytes(4, "little") + b"PAR1"


def batch_fixture() -> tuple[dict, dict[str, bytes]]:
    runid = "batch-run"
    roles = ("subcatchments", "channels", "hillslopes", "soils", "landuse")
    descriptor = {
        "schema_version": 1,
        "kind": "batch",
        "collection_key": "db17-batch",
        "source_revision": "db17-acceptance-1",
        "created_at": "2026-07-17T12:00:00Z",
        "master_url": MASTER_URL,
        "source_templates": {
            role: f"https://source.example.test/runs/{{runid}}/{role}" for role in roles
        },
        "members": [
            {
                "watershed_key": "batch-member",
                "runid": runid,
                "display_name": "Batch Member",
                "aliases": [],
            }
        ],
    }
    mapping = {MASTER_URL: geojson(runid)}
    for role in roles:
        mapping[descriptor["source_templates"][role].replace("{runid}", runid)] = (
            geojson(runid) if role in {"subcatchments", "channels"} else parquet()
        )
    return descriptor, mapping


def standalone_fixture() -> tuple[dict, dict[str, bytes]]:
    runid = "standalone-run"
    member_sources = {
        role: f"https://source.example.test/runs/{runid}/{role}"
        for role in sources.SOURCE_ROLES
    }
    descriptor = {
        "schema_version": 1,
        "kind": "standalone",
        "collection_key": "db17-standalone",
        "source_revision": "db17-acceptance-1",
        "created_at": "2026-07-17T12:00:00Z",
        "members": [
            {
                "watershed_key": "standalone-member",
                "runid": runid,
                "display_name": "Standalone Member",
                "aliases": [],
                "sources": member_sources,
            }
        ],
    }
    mapping = {
        url: geojson(runid) if role in sources.GEOJSON_ROLES else parquet()
        for role, url in member_sources.items()
    }
    return descriptor, mapping


class MappingFetcher:
    def __init__(self, mapping: dict[str, bytes]):
        self.mapping = mapping
        self.calls: list[str] = []

    def __call__(self, url: str, destination: Path, _headers: dict[str, str]) -> None:
        self.calls.append(url)
        try:
            content = self.mapping[url]
        except KeyError as error:
            raise sources.SourceFetchError("required synthetic source is missing") from error
        destination.write_bytes(content)


def accept(workspace: Path, *, require_test_namespace: bool = False) -> dict:
    workspace = workspace.resolve()
    if require_test_namespace and workspace != ACCEPTED_TEST_NAMESPACE:
        raise RuntimeError("acceptance workspace is not the approved test namespace")
    if workspace.is_symlink() or not workspace.is_dir():
        raise RuntimeError("acceptance workspace must be an existing real directory")
    before = {path.name for path in workspace.iterdir()}
    temporary = Path(tempfile.mkdtemp(prefix=".db17-accept-", dir=workspace))
    result = None
    try:
        client = artifacts.ArtifactClient(temporary / "store", temporary / "cache")
        batch_descriptor, batch_mapping = batch_fixture()
        batch_fetcher = MappingFetcher(batch_mapping)
        batch = sources.prepare_sources(
            batch_descriptor,
            client=client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=batch_fetcher,
        )

        def upstream_forbidden(_url: str, _path: Path, _headers: dict[str, str]) -> None:
            raise RuntimeError("receipt replay attempted an upstream read")

        replay = sources.prepare_sources(
            batch_descriptor,
            client=client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=upstream_forbidden,
            replay_receipt=batch.receipt,
        )
        standalone_descriptor, standalone_mapping = standalone_fixture()
        standalone = sources.prepare_sources(
            standalone_descriptor,
            client=client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=MappingFetcher(standalone_mapping),
        )
        object_count = sum(1 for path in client.object_root.rglob("*") if path.is_file())
        result = {
            "status": "passed",
            "checks": {
                "batch_exact_member": batch.member_count == 1,
                "custom_master_used": batch_fetcher.calls[0] == MASTER_URL,
                "receipt_replay_byte_identical": replay.index_bytes == batch.index_bytes,
                "standalone_exact_member": standalone.member_count == 1,
            },
            "batch_source_count": batch.source_count,
            "standalone_source_count": standalone.source_count,
            "immutable_object_count": object_count,
        }
        if not all(result["checks"].values()):
            raise RuntimeError("one or more acceptance checks failed")
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    if {path.name for path in workspace.iterdir()} != before:
        raise RuntimeError("acceptance did not restore the workspace")
    result["temporary_subtree_removed"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated DB17 source preparation acceptance.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--require-test-namespace", action="store_true")
    arguments = parser.parse_args()
    try:
        result = accept(
            arguments.workspace,
            require_test_namespace=arguments.require_test_namespace,
        )
    except (OSError, RuntimeError, sources.SourcePreparationError, artifacts.ArtifactError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
