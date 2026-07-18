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
sys.path.insert(0, str(REPOSITORY_ROOT / "release-tool" / "tests"))

from test_rhessys import ARTIFACT_BASE, MappingFetcher, fixture  # noqa: E402
from uwa_release_tool import artifacts, rhessys  # noqa: E402


ACCEPTED_TEST_NAMESPACE = Path("/wc1/utility-watershed-analytics-artifacts/v1/test")


def accept(workspace: Path, *, require_test_namespace: bool = False) -> dict:
    workspace = workspace.resolve()
    if require_test_namespace and workspace != ACCEPTED_TEST_NAMESPACE:
        raise RuntimeError("acceptance workspace is not the approved test namespace")
    if workspace.is_symlink() or not workspace.is_dir():
        raise RuntimeError("acceptance workspace must be an existing real directory")
    before = {path.name for path in workspace.iterdir()}
    temporary = Path(tempfile.mkdtemp(prefix=".db19-accept-", dir=workspace))
    result = None
    try:
        client = artifacts.ArtifactClient(temporary / "store", temporary / "cache")
        descriptor, mapping = fixture()
        prepared = rhessys.prepare_capability(
            descriptor,
            client=client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=MappingFetcher(mapping),
        )

        def upstream_forbidden(_url: str, _path: Path, _headers: dict[str, str]) -> None:
            raise RuntimeError("receipt replay attempted an upstream read")

        replay = rhessys.prepare_capability(
            descriptor,
            client=client,
            artifact_base_uri=ARTIFACT_BASE,
            replay_receipt=prepared.receipt,
            fetcher=upstream_forbidden,
        )
        references = [
            *(item["artifact"] for item in prepared.index["spatial_inputs"]),
            *(item["artifact"] for item in prepared.index["parquets"]),
            *(item["artifact"] for item in prepared.index["geotiffs"]),
        ]
        result = {
            "status": "passed",
            "checks": {
                "all_sources_content_addressed": all(
                    reference["sha256"] in reference["uri"] and reference["verified"]
                    for reference in references
                ),
                "exact_scenario_coverage": prepared.index["scenarios"]
                == descriptor["scenarios"],
                "geometry_revision_locked": prepared.index["geometry_revision"]
                == descriptor["geometry_revision"],
                "receipt_replay_byte_identical": replay.index_bytes
                == prepared.index_bytes,
                "representative_assets_refetched": all(
                    client.fetch(reference["sha256"]).byte_count == reference["bytes"]
                    for reference in references
                ),
            },
            "mode": prepared.index["mode"],
            "scenario_count": len(prepared.index["scenarios"]),
            "source_count": prepared.source_count,
            "removed_capabilities": rhessys.removed_capabilities(
                ["example-north", "example-south"], ["example-south"]
            ),
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
    parser = argparse.ArgumentParser(description="Run isolated DB19 RHESSys acceptance.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--require-test-namespace", action="store_true")
    arguments = parser.parse_args()
    try:
        result = accept(arguments.workspace, require_test_namespace=arguments.require_test_namespace)
    except (OSError, RuntimeError, rhessys.RhessysError, artifacts.ArtifactError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
