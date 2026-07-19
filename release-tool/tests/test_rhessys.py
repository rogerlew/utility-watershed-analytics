from __future__ import annotations

import copy
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from uwa_release_tool import artifacts, rhessys  # noqa: E402


ARTIFACT_BASE = "https://artifacts.example.test/v1/test/db19"
GEOMETRY_REVISION = "8" * 64


def varint(value: int) -> bytes:
    output = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        output.append(byte | 0x80 if value else byte)
        if not value:
            return bytes(output)


def integer(value: int) -> bytes:
    return varint((value << 1) ^ (value >> 63))


def schema_element(name: str, physical_type: int | None = None) -> bytes:
    output = bytearray()
    if physical_type is not None:
        output.extend((0x15,))
        output.extend(integer(physical_type))
        output.extend((0x38,))
    else:
        output.extend((0x48,))
    encoded = name.encode()
    output.extend(varint(len(encoded)))
    output.extend(encoded)
    output.append(0)
    return bytes(output)


def parquet_bytes(columns: list[tuple[str, int]] | None = None) -> bytes:
    columns = columns or [("basin_id", 2), ("year", 1), ("streamflow", 5)]
    elements = [schema_element("schema"), *(schema_element(name, value) for name, value in columns)]
    footer = bytearray((0x15,))
    footer.extend(integer(1))
    footer.append(0x19)
    footer.append((len(elements) << 4) | 12)
    for element in elements:
        footer.extend(element)
    footer.append(0x16)
    footer.extend(integer(2))
    footer.append(0)
    return b"PAR1\x01\x02" + bytes(footer) + len(footer).to_bytes(4, "little") + b"PAR1"


def geotiff_bytes(
    *,
    epsg: int = 4326,
    corrupt_sample: bool = False,
    transform_only: bool = False,
    nodata: str = "-9999",
) -> bytes:
    width = 2
    height = 2
    external_values = {
        33550: struct.pack("<3d", 1.0, 1.0, 0.0),
        33922: struct.pack("<6d", 0.0, 0.0, 0.0, 10.0, 20.0, 0.0),
        34735: struct.pack("<8H", 1, 1, 0, 1, 3072, 0, 1, epsg),
        42113: nodata.encode() + b"\x00",
    }
    if transform_only:
        external_values.pop(33550)
        external_values.pop(33922)
        external_values[34264] = struct.pack(
            "<16d",
            1.0, 0.0, 0.0, 10.0,
            0.0, -1.0, 0.0, 20.0,
            0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        )
    tag_specs = [
        (256, 4, 1, width),
        (257, 4, 1, height),
        (258, 3, 1, 8),
        (259, 3, 1, 1),
        (262, 3, 1, 1),
        (273, 4, 1, None),
        (277, 3, 1, 1),
        (278, 4, 1, height),
        (279, 4, 1, width * height),
    ]
    if transform_only:
        tag_specs.append((34264, 12, 16, None))
    else:
        tag_specs.extend(((33550, 12, 3, None), (33922, 12, 6, None)))
    tag_specs.extend([
        (34735, 3, 8, None),
        (42113, 2, len(external_values[42113]), None),
        (65000, 5, 1, 0),
    ])
    external_start = 8 + 2 + len(tag_specs) * 12 + 4
    offsets = {}
    external = bytearray()
    for tag in external_values:
        offsets[tag] = external_start + len(external)
        external.extend(external_values[tag])
    pixel_offset = external_start + len(external)
    output = bytearray(b"II" + struct.pack("<H", 42) + struct.pack("<I", 8))
    output.extend(struct.pack("<H", len(tag_specs)))
    for tag, value_type, count, value in tag_specs:
        output.extend(struct.pack("<HHI", tag, value_type, count))
        if tag == 273:
            output.extend(struct.pack("<I", pixel_offset + (100 if corrupt_sample else 0)))
        elif tag in offsets:
            output.extend(struct.pack("<I", offsets[tag]))
        elif value_type == 3:
            output.extend(struct.pack("<H", value) + b"\x00\x00")
        else:
            output.extend(struct.pack("<I", value))
    output.extend(struct.pack("<I", 0))
    output.extend(external)
    output.extend(b"\x01\x02\x03\x04")
    return bytes(output)


def geometry_bytes() -> bytes:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"hillID": 1},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[10.0, 20.0], [11.0, 20.0], [10.0, 21.0], [10.0, 20.0]]],
                    },
                }
            ],
        },
        separators=(",", ":"),
    ).encode()


class MappingFetcher:
    def __init__(self, mapping: dict[str, bytes]):
        self.mapping = mapping
        self.calls = 0

    def __call__(self, url: str, destination: Path, _headers: dict[str, str]) -> None:
        self.calls += 1
        destination.write_bytes(self.mapping[url])


def source_fields(url: str, content: bytes) -> dict:
    return {
        "source_url": url,
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "source_bytes": len(content),
        "geometry_revision": GEOMETRY_REVISION,
    }


def fixture() -> tuple[dict, dict[str, bytes]]:
    parquet = parquet_bytes()
    spatial = geotiff_bytes()
    burned = geotiff_bytes()
    unburned = geotiff_bytes()
    geometry = geometry_bytes()
    mapping = {
        "https://source.example.test/spatial.tif": spatial,
        "https://source.example.test/basin.parquet": parquet,
        "https://source.example.test/burned.tif": burned,
        "https://source.example.test/unburned.tif": unburned,
        "https://source.example.test/hillslopes.geojson": geometry,
    }
    raster = {
        "crs": "EPSG:4326",
        "bounds": [10.0, 18.0, 12.0, 20.0],
        "dimensions": [2, 2],
        "bands": 1,
        "nodata": -9999,
        "required_for_activation": True,
    }
    descriptor = {
        "schema_version": 1,
        "kind": "rhessys-capability",
        "collection_key": "example-collection",
        "watershed_key": "example-north",
        "runid": "illustrative/north",
        "source_revision": "fixture-v1",
        "created_at": "2026-07-18T12:00:00Z",
        "mode": "both",
        "geometry_revision": GEOMETRY_REVISION,
        "scenarios": [
            {"key": "burned", "variables": ["streamflow"]},
            {"key": "unburned", "variables": ["streamflow"]},
        ],
        "spatial_inputs": [
            {
                "role": "dem",
                **source_fields("https://source.example.test/spatial.tif", spatial),
                **raster,
            }
        ],
        "parquets": [
            {
                "dataset_key": "burned-basin",
                "scenario": "burned",
                "role": "basin",
                **source_fields("https://source.example.test/basin.parquet", parquet),
                "spatial_id_field": "basin_id",
                "columns": [
                    {"name": "basin_id", "physical_type": "INT64"},
                    {"name": "year", "physical_type": "INT32"},
                    {"name": "streamflow", "physical_type": "DOUBLE"},
                ],
                "variables": [{"name": "streamflow", "units": "mm"}],
                "year_range": [1980, 2020],
                "required_for_activation": True,
            }
        ],
        "geometries": [
            {
                "scale": "hillslope",
                "scenarios": ["burned", "unburned"],
                **source_fields(
                    "https://source.example.test/hillslopes.geojson", geometry
                ),
                "source_crs": "EPSG:4326",
                "required_for_activation": True,
            }
        ],
        "geotiffs": [
            {
                "scenario": "burned",
                "variable": "streamflow",
                **source_fields("https://source.example.test/burned.tif", burned),
                **raster,
            },
            {
                "scenario": "unburned",
                "variable": "streamflow",
                **source_fields("https://source.example.test/unburned.tif", unburned),
                **raster,
            },
        ],
    }
    return descriptor, mapping


class RhessysInspectionTests(unittest.TestCase):
    def test_reads_parquet_footer_schema_and_representative_bytes(self):
        result = rhessys.inspect_parquet(parquet_bytes())
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["columns"][2], {"name": "streamflow", "physical_type": "DOUBLE"})
        self.assertEqual(result["sample_bytes_read"], 2)

    def test_reads_geotiff_metadata_and_representative_strip(self):
        result = rhessys.inspect_geotiff(geotiff_bytes())
        self.assertEqual(result["crs"], "EPSG:4326")
        self.assertEqual(result["bounds"], [10.0, 18.0, 12.0, 20.0])
        self.assertEqual(result["sample_bytes_read"], 1)
        transformed = rhessys.inspect_geotiff(geotiff_bytes(transform_only=True))
        self.assertEqual(transformed["bounds"], [10.0, 18.0, 12.0, 20.0])
        self.assertIsNone(rhessys.inspect_geotiff(geotiff_bytes(nodata="NaN "))["nodata"])

    def test_corrupt_parquet_and_geotiff_are_rejected(self):
        with self.assertRaises(rhessys.RhessysFormatError):
            rhessys.inspect_parquet(b"PAR1brokenPAR1")
        with self.assertRaises(rhessys.RhessysFormatError):
            rhessys.inspect_geotiff(geotiff_bytes(corrupt_sample=True))


class RhessysDescriptorTests(unittest.TestCase):
    def test_dynamic_and_precomputed_modes_are_supported(self):
        descriptor, _ = fixture()
        dynamic = copy.deepcopy(descriptor)
        dynamic["mode"] = "dynamic"
        dynamic["geotiffs"] = []
        self.assertEqual(rhessys.validate_descriptor(dynamic)["mode"], "dynamic")

        precomputed = copy.deepcopy(descriptor)
        precomputed["mode"] = "precomputed"
        precomputed["spatial_inputs"] = []
        precomputed["parquets"] = []
        precomputed["geometries"] = []
        self.assertEqual(
            rhessys.validate_descriptor(precomputed)["mode"], "precomputed"
        )

    def test_deployed_uppercase_underscore_scenario_ids_are_supported(self):
        descriptor, _ = fixture()
        descriptor["scenarios"][0]["key"] = "Pspread_fire_1yr_change"
        descriptor["parquets"][0]["scenario"] = "Pspread_fire_1yr_change"
        descriptor["geometries"][0]["scenarios"][0] = "Pspread_fire_1yr_change"
        descriptor["geotiffs"][0]["scenario"] = "Pspread_fire_1yr_change"
        normalized = rhessys.validate_descriptor(descriptor)
        self.assertEqual(normalized["scenarios"][0]["key"], "Pspread_fire_1yr_change")

    def test_missing_and_partial_scenarios_are_rejected(self):
        descriptor, _ = fixture()
        missing = copy.deepcopy(descriptor)
        missing["scenarios"] = []
        with self.assertRaisesRegex(rhessys.RhessysDescriptorError, "scenarios"):
            rhessys.validate_descriptor(missing)
        partial = copy.deepcopy(descriptor)
        partial["geotiffs"].pop()
        with self.assertRaisesRegex(rhessys.RhessysDescriptorError, "exactly cover"):
            rhessys.validate_descriptor(partial)

    def test_renamed_variable_and_geometry_revision_mismatch_are_rejected(self):
        descriptor, _ = fixture()
        renamed = copy.deepcopy(descriptor)
        renamed["parquets"][0]["variables"][0]["name"] = "renamed"
        with self.assertRaisesRegex(rhessys.RhessysDescriptorError, "lacks"):
            rhessys.validate_descriptor(renamed)
        geometry = copy.deepcopy(descriptor)
        geometry["parquets"][0]["geometry_revision"] = "9" * 64
        with self.assertRaisesRegex(rhessys.RhessysDescriptorError, "geometry revision"):
            rhessys.validate_descriptor(geometry)

    def test_capability_removal_is_explicit_set_difference(self):
        self.assertEqual(
            rhessys.removed_capabilities(["example-north", "example-south"], ["example-south"]),
            ["example-north"],
        )


class RhessysPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.client = artifacts.ArtifactClient(self.root / "store", self.root / "cache")

    def tearDown(self):
        self.temporary.cleanup()

    def test_prepares_exact_index_and_replays_without_upstream(self):
        descriptor, mapping = fixture()
        fetcher = MappingFetcher(mapping)
        first = rhessys.prepare_capability(
            descriptor,
            client=self.client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=fetcher,
        )
        self.assertEqual(fetcher.calls, 5)
        self.assertEqual(first.index["mode"], "both")
        self.assertEqual(len(first.index["scenarios"]), 2)
        self.assertEqual(first.source_count, 5)
        replay_fetcher = MappingFetcher({})
        replay = rhessys.prepare_capability(
            descriptor,
            client=self.client,
            artifact_base_uri=ARTIFACT_BASE,
            replay_receipt=first.receipt,
            fetcher=replay_fetcher,
        )
        self.assertEqual(replay_fetcher.calls, 0)
        self.assertEqual(replay.index_bytes, first.index_bytes)
        self.assertEqual(replay.receipt_bytes, first.receipt_bytes)

    def test_parquet_schema_drift_and_crs_mismatch_are_rejected(self):
        descriptor, mapping = fixture()
        drifted = parquet_bytes([("basin_id", 2), ("year", 1), ("streamflow", 4)])
        mapping["https://source.example.test/basin.parquet"] = drifted
        descriptor["parquets"][0].update(
            source_sha256=hashlib.sha256(drifted).hexdigest(), source_bytes=len(drifted)
        )
        with self.assertRaisesRegex(rhessys.RhessysFormatError, "schema differs"):
            rhessys.prepare_capability(
                descriptor,
                client=self.client,
                artifact_base_uri=ARTIFACT_BASE,
                fetcher=MappingFetcher(mapping),
            )

    def test_overlapping_parquet_query_coordinates_are_rejected(self):
        descriptor, _ = fixture()
        duplicate = copy.deepcopy(descriptor["parquets"][0])
        duplicate["dataset_key"] = "other-burned-basin"
        descriptor["parquets"].append(duplicate)
        with self.assertRaisesRegex(rhessys.RhessysDescriptorError, "coordinates overlap"):
            rhessys.validate_descriptor(descriptor)

        descriptor, mapping = fixture()
        wrong_crs = geotiff_bytes(epsg=3857)
        mapping["https://source.example.test/burned.tif"] = wrong_crs
        descriptor["geotiffs"][0].update(
            source_sha256=hashlib.sha256(wrong_crs).hexdigest(), source_bytes=len(wrong_crs)
        )
        with self.assertRaisesRegex(rhessys.RhessysFormatError, "metadata differs"):
            rhessys.prepare_capability(
                descriptor,
                client=self.client,
                artifact_base_uri=ARTIFACT_BASE,
                fetcher=MappingFetcher(mapping),
            )

    def test_interrupted_publication_leaves_no_partial_asset(self):
        descriptor, mapping = fixture()

        def interrupt(_operation: str, _byte_count: int) -> None:
            raise RuntimeError("fixture interruption")

        client = artifacts.ArtifactClient(
            self.root / "interrupted-store",
            self.root / "interrupted-cache",
            chunk_size=1,
            progress=interrupt,
        )
        with self.assertRaises(artifacts.ArtifactTransferError):
            rhessys.prepare_capability(
                descriptor,
                client=client,
                artifact_base_uri=ARTIFACT_BASE,
                fetcher=MappingFetcher(mapping),
            )
        partial = self.root / "interrupted-store" / ".partial"
        self.assertFalse(partial.exists() and any(partial.iterdir()))


if __name__ == "__main__":
    unittest.main()
