#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "release-tool"))
sys.path.insert(0, str(REPOSITORY_ROOT / "server"))

from server.watershed.rhessys_spatial.registry import SPATIAL_INPUT_REGISTRY  # noqa: E402
from uwa_release_tool.artifacts import ArtifactClient  # noqa: E402
from uwa_release_tool.rhessys import (  # noqa: E402
    canonical_json,
    inspect_geotiff,
    inspect_geometry,
    inspect_parquet,
    prepare_capability,
)
from uwa_release_tool.sources import fetch_https  # noqa: E402


CREATED_AT = "2026-07-19T01:48:07Z"
GATE_BASE = (
    "https://wepp.cloud/weppcloud/runs/aversive-forestry/"
    "disturbed9002_wbt/download/rhessys"
)
ARTIFACT_FILENAMES = {
    "streamflow": "streamflow.tif",
    "lai": "lai.tif",
    "ET": "ET.tif",
    "aboveground_biomass": "Aboveground_Biomass__Kg_m2_.tif",
    "nitrate": "Nitrate__mg_m2_day_.tif",
    "ammonium": "Ammonium__mg_m2_day_.tif",
    "doc": "DOC__mg_m2_day_.tif",
    "don": "DON__mg_m2_day_.tif",
}
SOOKE_SCENARIOS = {
    "Sooke09": (
        "baseline",
        "heavy_thin_1yr_change",
        "heavy_thin_1yr_diff",
        "heavy_thin_5yr_change",
        "Pspread_fire_1yr_change",
        "Pspread_fire_1yr_diff",
        "Pspread_fire_5yr_change",
    ),
    "Sooke15": (
        "baseline",
        "heavy_thin_1yr_change",
        "heavy_thin_5yr_change",
        "Pspread_fire_1yr_change",
        "Pspread_fire_5yr_change",
    ),
}
GATE_VARIABLE_UNITS = {
    "streamflow": "mm/day",
    "baseflow": "mm/day",
    "return": "mm/day",
    "trans": "mm/day",
    "evap": "mm/day",
    "lai": "m2/m2",
    "gpsn": "gC/m2/day",
    "plantc": "kgC/m2",
    "et": "mm/yr",
    "plant_c": "kgC/m2",
    "litter_c": "kgC/m2",
    "soil_c": "kgC/m2",
}
GATE_PARQUETS = (
    ("basin", "basin.daily.parquet", "basinID", ("streamflow", "baseflow", "return", "trans", "evap")),
    ("basin", "grow_basin.daily.parquet", "basinID", ("lai", "gpsn", "plantc")),
    ("hillslope", "hillslope.daily.parquet", "hillID", ("streamflow", "baseflow", "return", "trans", "evap")),
    ("hillslope", "grow_hillslope.daily.parquet", "basinID", ("lai", "gpsn", "plantc")),
    ("patch", "patch.yearly.parquet", "patchID", ("et",)),
    ("patch", "grow_patch.yearly.parquet", "patchID", ("plant_c", "litter_c", "soil_c")),
)
GATE_GEOMETRIES = (
    (
        "hillslope",
        ("S1", "S2", "S4b"),
        "masked_tol_1000cleaned_hillslop.geojson",
    ),
    ("patch", ("S1", "S4b"), "masked_daymet_patchID_1985.geojson"),
    ("patch", ("S2",), "masked_daymet_patchID_2021.geojson"),
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-namespace", required=True, type=Path)
    parser.add_argument("--cache-root", required=True, type=Path)
    parser.add_argument("--staging-parent", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--artifact-base-uri", required=True)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def source_url_for_sooke(run: str, scenario: str, filename: str) -> str:
    return (
        "https://wepp.cloud/weppcloud/runs/"
        f"batch;;victoria-ca-2026-sbs;;{run}/disturbed_wbt/"
        f"download/rhessys/maps/{scenario}/{filename}"
    )


def gate_urls() -> list[str]:
    urls = [
        f"{GATE_BASE}/spatial_inputs_and_climates/{filename}"
        for filename in sorted(SPATIAL_INPUT_REGISTRY)
    ]
    for scenario in ("S1", "S2", "S4b"):
        urls.extend(
            f"{GATE_BASE}/scenarios/{scenario}/{filename}"
            for _, filename, _, _ in GATE_PARQUETS
        )
    urls.extend(
        f"{GATE_BASE}/spatial_inputs_and_climates/{filename}"
        for _, _, filename in GATE_GEOMETRIES
    )
    return urls


def sooke_urls() -> list[str]:
    return [
        source_url_for_sooke(run, scenario, filename)
        for run, scenarios in SOOKE_SCENARIOS.items()
        for scenario in scenarios
        for filename in ARTIFACT_FILENAMES.values()
    ]


def download_sources(urls: list[str], root: Path, workers: int) -> dict[str, Path]:
    if workers < 1 or workers > 16:
        raise ValueError("workers must be between 1 and 16")
    mapping = {
        url: root / hashlib.sha256(url.encode()).hexdigest()
        for url in sorted(set(urls))
    }

    def download(item: tuple[str, Path]) -> tuple[str, Path]:
        url, destination = item
        if destination.exists():
            if destination.is_symlink() or not destination.is_file() or destination.stat().st_size <= 0:
                raise ValueError("retained DB28 staging input is invalid")
            return url, destination
        fetch_https(url, destination, {})
        return url, destination

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(download, item) for item in mapping.items()]
        for future in as_completed(futures):
            future.result()
    return mapping


def source_fields(path: Path, url: str, revision: str) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "source_url": url,
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "source_bytes": len(content),
        "geometry_revision": revision,
    }


def bundle_revision(mapping: dict[str, Path], urls: list[str]) -> str:
    inventory = []
    for url in sorted(urls):
        content = mapping[url].read_bytes()
        inventory.append(
            {
                "url": url,
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )
    return hashlib.sha256(canonical_json(inventory)).hexdigest()


def raster_fields(path: Path) -> dict[str, Any]:
    inspection = inspect_geotiff(path.read_bytes())
    return {
        key: inspection[key]
        for key in ("crs", "bounds", "dimensions", "bands", "nodata")
    } | {"required_for_activation": True}


def canonical_role(filename: str) -> str:
    role = re.sub(r"[^a-z0-9]+", "-", filename.removesuffix(".tif").lower()).strip("-")
    if not role:
        raise ValueError("empty spatial role")
    return role


def build_gate_descriptor(mapping: dict[str, Path]) -> dict[str, Any]:
    urls = gate_urls()
    revision = bundle_revision(mapping, urls)
    spatial_inputs = []
    for filename in sorted(SPATIAL_INPUT_REGISTRY):
        url = f"{GATE_BASE}/spatial_inputs_and_climates/{filename}"
        spatial_inputs.append(
            {
                "role": canonical_role(filename),
                **source_fields(mapping[url], url, revision),
                **raster_fields(mapping[url]),
            }
        )
    parquets = []
    for scenario in ("S1", "S2", "S4b"):
        for role, filename, spatial_id, variables in GATE_PARQUETS:
            url = f"{GATE_BASE}/scenarios/{scenario}/{filename}"
            inspection = inspect_parquet(mapping[url].read_bytes())
            columns = {item["name"] for item in inspection["columns"]}
            required = {spatial_id, "year", *variables}
            if not required.issubset(columns):
                missing = sorted(required - columns)
                raise ValueError(f"{scenario}/{filename} lacks columns {missing}")
            parquets.append(
                {
                    "dataset_key": canonical_role(f"{scenario}-{filename}"),
                    "scenario": scenario,
                    "role": role,
                    **source_fields(mapping[url], url, revision),
                    "spatial_id_field": spatial_id,
                    "columns": inspection["columns"],
                    "variables": [
                        {"name": variable, "units": GATE_VARIABLE_UNITS[variable]}
                        for variable in variables
                    ],
                    "year_range": [1985, 2023 if role == "patch" else 2024],
                    "required_for_activation": True,
                }
            )
    geometries = []
    for scale, scenarios, filename in GATE_GEOMETRIES:
        url = f"{GATE_BASE}/spatial_inputs_and_climates/{filename}"
        inspect_geometry(mapping[url].read_bytes())
        geometries.append(
            {
                "scale": scale,
                "scenarios": list(scenarios),
                **source_fields(mapping[url], url, revision),
                "source_crs": "EPSG:26910",
                "required_for_activation": True,
            }
        )
    return {
        "schema_version": 1,
        "kind": "rhessys-capability",
        "collection_key": "gate-creek",
        "watershed_key": "gate-creek",
        "runid": "aversive-forestry",
        "source_revision": f"weppcloud-{revision[:16]}",
        "created_at": CREATED_AT,
        "mode": "dynamic",
        "geometry_revision": revision,
        "scenarios": [
            {"key": scenario, "variables": list(GATE_VARIABLE_UNITS)}
            for scenario in ("S1", "S2", "S4b")
        ],
        "spatial_inputs": spatial_inputs,
        "parquets": parquets,
        "geometries": geometries,
        "geotiffs": [],
    }


def build_sooke_descriptor(run: str, mapping: dict[str, Path]) -> dict[str, Any]:
    urls = [
        source_url_for_sooke(run, scenario, filename)
        for scenario in SOOKE_SCENARIOS[run]
        for filename in ARTIFACT_FILENAMES.values()
    ]
    revision = bundle_revision(mapping, urls)
    geotiffs = []
    for scenario in SOOKE_SCENARIOS[run]:
        for variable, filename in ARTIFACT_FILENAMES.items():
            url = source_url_for_sooke(run, scenario, filename)
            geotiffs.append(
                {
                    "scenario": scenario,
                    "variable": variable,
                    **source_fields(mapping[url], url, revision),
                    **raster_fields(mapping[url]),
                }
            )
    return {
        "schema_version": 1,
        "kind": "rhessys-capability",
        "collection_key": "victoria-ca",
        "watershed_key": f"victoria-ca-{run.lower()}",
        "runid": f"batch;;victoria-ca-2026-sbs;;{run}",
        "source_revision": f"weppcloud-{revision[:16]}",
        "created_at": CREATED_AT,
        "mode": "precomputed",
        "geometry_revision": revision,
        "scenarios": [
            {"key": scenario, "variables": list(ARTIFACT_FILENAMES)}
            for scenario in SOOKE_SCENARIOS[run]
        ],
        "spatial_inputs": [],
        "parquets": [],
        "geometries": [],
        "geotiffs": geotiffs,
    }


def write_new_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2, sort_keys=True)
        stream.write("\n")


def publish_descriptor(
    descriptor: dict[str, Any],
    mapping: dict[str, Path],
    client: ArtifactClient,
    artifact_base_uri: str,
) -> Any:
    def staged_fetch(url: str, destination: Path, _headers: dict[str, str]) -> None:
        shutil.copyfile(mapping[url], destination)

    return prepare_capability(
        descriptor,
        client=client,
        artifact_base_uri=artifact_base_uri,
        fetcher=staged_fetch,
    )


def main() -> int:
    arguments = parse_arguments()
    arguments.output_root.mkdir(parents=True, exist_ok=True)
    outputs = {
        name: arguments.output_root / name
        for name in (
            "gate-creek-rhessys-descriptor.json",
            "gate-creek-rhessys-index.json",
            "gate-creek-rhessys-receipt.json",
            "victoria-ca-sooke09-rhessys-descriptor.json",
            "victoria-ca-sooke09-rhessys-index.json",
            "victoria-ca-sooke09-rhessys-receipt.json",
            "victoria-ca-sooke15-rhessys-descriptor.json",
            "victoria-ca-sooke15-rhessys-index.json",
            "victoria-ca-sooke15-rhessys-receipt.json",
        )
    }
    existing = [str(path) for path in outputs.values() if path.exists() or path.is_symlink()]
    if existing:
        raise FileExistsError(f"DB28 output already exists: {existing[0]}")
    urls = gate_urls() + sooke_urls()
    staging_root = arguments.staging_parent / "db28-rhessys-staging"
    staging_root.mkdir(mode=0o700, parents=False, exist_ok=True)
    if staging_root.is_symlink() or not staging_root.is_dir():
        raise ValueError("DB28 staging root is invalid")
    mapping = download_sources(urls, staging_root, arguments.workers)
    try:
        descriptors = {
            "gate-creek": build_gate_descriptor(mapping),
            "victoria-ca-sooke09": build_sooke_descriptor("Sooke09", mapping),
            "victoria-ca-sooke15": build_sooke_descriptor("Sooke15", mapping),
        }
        client = ArtifactClient(arguments.store_namespace, arguments.cache_root)
        summary = {}
        for key, descriptor in descriptors.items():
            descriptor_path = outputs[f"{key}-rhessys-descriptor.json"]
            write_new_json(descriptor_path, descriptor)
            result = publish_descriptor(
                descriptor, mapping, client, arguments.artifact_base_uri
            )
            outputs[f"{key}-rhessys-index.json"].write_bytes(result.index_bytes)
            outputs[f"{key}-rhessys-receipt.json"].write_bytes(result.receipt_bytes)
            summary[key] = {
                "sources": result.source_count,
                "index_sha256": result.index_artifact.digest,
                "receipt_sha256": result.receipt_artifact.digest,
                "source_bytes": sum(
                    item["bytes"] for item in result.receipt["sources"]
                ),
            }
    except Exception:
        print(
            json.dumps(
                {"status": "hold", "retained_staging": str(staging_root)},
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise
    shutil.rmtree(staging_root)
    print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
