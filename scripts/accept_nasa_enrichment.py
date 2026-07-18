#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "release-tool"))

from uwa_release_tool import artifacts, enrichment, sources  # noqa: E402


ACCEPTED_TEST_NAMESPACE = Path("/wc1/utility-watershed-analytics-artifacts/v1/test")
ARTIFACT_BASE = "https://artifacts.example.test/db18-acceptance"
MASTER_URL = "https://source.example.test/nasa/custom-master.geojson"
ENRICHMENT_URL = "https://source.example.test/WWS_Watersheds_HUC10_Merged.geojson"


def geometry(offset: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [[-117 + offset, 46], [-116.9 + offset, 46], [-116.9 + offset, 46.1], [-117 + offset, 46]]
        ],
    }


def target_feature(code: str, offset: float) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "runid": f"{enrichment.TARGET_RUNID_PREFIX}{code}",
            "WWS_Code": code,
            "target_only": code,
        },
        "geometry": geometry(offset),
    }


def source_feature(code: str, offset: float) -> dict:
    properties = {
        "PWS_ID": f"PWS-{code}",
        "SrcName": f"Source {code}",
        "PWS_Name": f"Utility {code}",
        "County_Nam": "Example County",
        "State": "OR",
        "HUC10_ID": f"HUC-{code}",
        "HUC10_Name": f"HUC {code}",
        "WWS_Code": code,
        "SrcType": "Public",
        "Shape_Leng": 1.0,
        "Shape_Area": 2.0,
        "outlet_lon_lat": [-116.95, 46.05],
        "runid": f"batch;;nasa-roses-2025;;{code}",
    }
    return {"type": "Feature", "properties": properties, "geometry": geometry(offset)}


def geojson(*features: dict) -> bytes:
    return sources.canonical_json({"type": "FeatureCollection", "features": list(features)})


def parquet() -> bytes:
    metadata = b"db18-acceptance"
    return b"PAR1" + metadata + len(metadata).to_bytes(4, "little") + b"PAR1"


def fixture() -> tuple[dict, dict[str, bytes]]:
    target_bytes = geojson(target_feature("A", 0.0), target_feature("B", 0.2))
    source_bytes = geojson(source_feature("A", 2.0), source_feature("EXTRA", 2.2))
    roles = ("subcatchments", "channels", "hillslopes", "soils", "landuse")
    descriptor = {
        "schema_version": 1,
        "kind": "batch",
        "collection_key": "nasa-roses",
        "source_revision": "db18-acceptance-1",
        "created_at": "2026-07-17T12:00:00Z",
        "master_url": MASTER_URL,
        "source_templates": {
            role: f"https://source.example.test/runs/{{runid}}/{role}" for role in roles
        },
        "enrichment": {
            "type": "nasa-202606-wws-code",
            "source_url": ENRICHMENT_URL,
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "source_bytes": len(source_bytes),
            "code_git_commit": "1" * 40,
            "validator_image_digest": f"sha256:{'2' * 64}",
        },
        "members": [
            {
                "watershed_key": f"nasa-{code.lower()}",
                "runid": f"{enrichment.TARGET_RUNID_PREFIX}{code}",
                "display_name": f"NASA {code}",
                "aliases": [],
            }
            for code in ("A", "B")
        ],
    }
    mapping = {MASTER_URL: target_bytes, ENRICHMENT_URL: source_bytes}
    for member in descriptor["members"]:
        for role in roles:
            url = descriptor["source_templates"][role].replace("{runid}", member["runid"])
            mapping[url] = (
                geojson(target_feature("A", 0.0))
                if role in {"subcatchments", "channels"}
                else parquet()
            )
    return descriptor, mapping


class MappingFetcher:
    def __init__(self, mapping: dict[str, bytes]):
        self.mapping = mapping

    def __call__(self, url: str, destination: Path, _headers: dict[str, str]) -> None:
        destination.write_bytes(self.mapping[url])


def read_artifact(client: artifacts.ArtifactClient, reference: dict) -> dict:
    return json.loads(client.fetch(reference["sha256"]).path.read_bytes())


def accept(workspace: Path, *, require_test_namespace: bool = False) -> dict:
    workspace = workspace.resolve()
    if require_test_namespace and workspace != ACCEPTED_TEST_NAMESPACE:
        raise RuntimeError("acceptance workspace is not the approved test namespace")
    if workspace.is_symlink() or not workspace.is_dir():
        raise RuntimeError("acceptance workspace must be an existing real directory")
    before = {path.name for path in workspace.iterdir()}
    temporary = Path(tempfile.mkdtemp(prefix=".db18-accept-", dir=workspace))
    result = None
    try:
        client = artifacts.ArtifactClient(temporary / "store", temporary / "cache")
        descriptor, mapping = fixture()
        prepared = sources.prepare_sources(
            descriptor,
            client=client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=MappingFetcher(mapping),
        )
        lineage = read_artifact(client, prepared.index["members"][0]["transformation_lineage"])
        report = read_artifact(client, lineage["validation_report"])
        enriched = read_artifact(client, lineage["output"])
        checks = {check["code"]: check["count"] for check in report["checks"]}

        def upstream_forbidden(_url: str, _path: Path, _headers: dict[str, str]) -> None:
            raise RuntimeError("receipt replay attempted an upstream read")

        replay = sources.prepare_sources(
            descriptor,
            client=client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=upstream_forbidden,
            replay_receipt=prepared.receipt,
        )
        result = {
            "status": "passed",
            "checks": {
                "exact_member_count": prepared.member_count == 2,
                "geometry_preserved": checks["preserved-geometry"] == 2,
                "historical_runids_absent": "nasa-roses-2025" not in json.dumps(enriched),
                "source_differences_recorded": checks["source-runid-differences"] == 1
                and checks["source-geometry-differences"] == 1,
                "receipt_replay_byte_identical": replay.index_bytes == prepared.index_bytes,
                "runids_preserved": checks["preserved-runids"] == 2,
            },
            "matched": lineage["counts"]["matched"],
            "target_unmatched": checks["target-unmatched"],
            "source_unmatched": checks["source-unmatched"],
            "source_count": prepared.source_count,
            "lineage_field_count": len(lineage["field_decisions"]),
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
    parser = argparse.ArgumentParser(description="Run isolated DB18 NASA enrichment acceptance.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--require-test-namespace", action="store_true")
    arguments = parser.parse_args()
    try:
        result = accept(arguments.workspace, require_test_namespace=arguments.require_test_namespace)
    except (OSError, RuntimeError, sources.SourcePreparationError, artifacts.ArtifactError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
