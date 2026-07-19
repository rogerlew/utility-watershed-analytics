from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from uwa_release_tool import artifacts, sources  # noqa: E402


ARTIFACT_BASE = "https://artifacts.example.test/db17"
MASTER_URL = "https://source.example.test/resources/custom-master-name.geojson"
ROLES = ("subcatchments", "channels", "hillslopes", "soils", "landuse")


def feature(runid: str, offset: float = 0.0) -> dict:
    return {
        "type": "Feature",
        "properties": {"runid": runid, "source_label": f"source-{runid}"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-117.0 + offset, 46.0],
                    [-116.9 + offset, 46.0],
                    [-116.9 + offset, 46.1],
                    [-117.0 + offset, 46.0],
                ]
            ],
        },
    }


def child_feature(runid: str, role: str, offset: float = 0.0) -> dict:
    document = feature(runid, offset)
    document["properties"].update(TopazID=1, WeppID=2)
    if role == "channels":
        document["properties"]["Order"] = 3
    return document


def geojson(*features: dict) -> bytes:
    return sources.canonical_json({"type": "FeatureCollection", "features": list(features)})


def parquet(payload: bytes = b"metadata") -> bytes:
    return b"PAR1" + payload + len(payload).to_bytes(4, "little") + b"PAR1"


def batch_descriptor() -> dict:
    return {
        "schema_version": 1,
        "kind": "batch",
        "collection_key": "fixture-batch",
        "source_revision": "fixture-revision-1",
        "created_at": "2026-07-17T12:00:00Z",
        "master_url": MASTER_URL,
        "source_templates": {
            role: f"https://source.example.test/runs/{{runid}}/{role}"
            for role in ROLES
        },
        "members": [
            {
                "watershed_key": "north",
                "runid": "run-north",
                "display_name": "North",
                "aliases": ["north-old"],
            },
            {
                "watershed_key": "south",
                "runid": "run-south",
                "display_name": "South",
                "aliases": [],
            },
        ],
    }


def standalone_descriptor() -> dict:
    runid = "standalone-run"
    return {
        "schema_version": 1,
        "kind": "standalone",
        "collection_key": "fixture-standalone",
        "source_revision": "fixture-standalone-1",
        "created_at": "2026-07-17T12:00:00Z",
        "members": [
            {
                "watershed_key": "standalone",
                "runid": runid,
                "display_name": "Standalone",
                "aliases": [],
                "sources": {
                    role: f"https://source.example.test/runs/{runid}/{role}"
                    for role in sources.SOURCE_ROLES
                },
            }
        ],
    }


def batch_mapping(descriptor: dict | None = None) -> dict[str, bytes]:
    descriptor = descriptor or batch_descriptor()
    mapping = {MASTER_URL: geojson(feature("run-north"), feature("run-south", 0.2))}
    for member in descriptor["members"]:
        runid = member["runid"]
        for role in ROLES:
            url = descriptor["source_templates"][role].replace("{runid}", runid)
            mapping[url] = (
                geojson(child_feature(runid, role))
                if role in {"subcatchments", "channels"}
                else parquet()
            )
    return mapping


def standalone_mapping(descriptor: dict | None = None) -> dict[str, bytes]:
    descriptor = descriptor or standalone_descriptor()
    member = descriptor["members"][0]
    return {
        url: (
            geojson(child_feature(member["runid"], role))
            if role in sources.GEOJSON_ROLES
            else parquet()
        )
        for role, url in member["sources"].items()
    }


class MappingFetcher:
    def __init__(self, mapping: dict[str, bytes | Exception]):
        self.mapping = mapping
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, destination: Path, headers: dict[str, str]) -> None:
        self.calls.append((url, dict(headers)))
        value = self.mapping.get(url, sources.SourceFetchError("required source is missing"))
        if isinstance(value, Exception):
            raise value
        destination.write_bytes(value)


class SourcePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.client = artifacts.ArtifactClient(self.root / "store", self.root / "cache")

    def tearDown(self):
        self.temporary.cleanup()

    def prepare(self, descriptor: dict, mapping: dict[str, bytes | Exception]):
        fetcher = MappingFetcher(mapping)
        result = sources.prepare_sources(
            descriptor,
            client=self.client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=fetcher,
        )
        return result, fetcher

    def test_batch_custom_master_publishes_exact_index_and_replays_without_upstream(self):
        descriptor = batch_descriptor()
        result, fetcher = self.prepare(descriptor, batch_mapping(descriptor))
        self.assertEqual(fetcher.calls[0][0], MASTER_URL)
        self.assertEqual(result.member_count, 2)
        self.assertEqual(result.source_count, 11)
        self.assertEqual([member["runid"] for member in result.index["members"]], ["run-north", "run-south"])
        self.assertTrue(
            all(
                reference["uri"].startswith(f"{ARTIFACT_BASE}/objects/sha256/")
                and reference["verified"]
                for member in result.index["members"]
                for reference in member["artifacts"].values()
            )
        )

        def upstream_forbidden(_url: str, _path: Path, _headers: dict[str, str]) -> None:
            raise AssertionError("replay called upstream")

        replay = sources.prepare_sources(
            descriptor,
            client=self.client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=upstream_forbidden,
            replay_receipt=result.receipt,
        )
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.index_bytes, result.index_bytes)
        self.assertEqual(replay.index_artifact.digest, result.index_artifact.digest)
        self.assertEqual(replay.receipt_bytes, result.receipt_bytes)

    def test_reviewed_feature_id_prefix_filters_a_broader_public_master(self):
        descriptor = batch_descriptor()
        descriptor["master_identity"] = {
            "location": "feature-id",
            "prefix": "run-",
        }
        master = json.loads(geojson(feature("run-north"), feature("run-south", 0.2)))
        for feature_document in master["features"]:
            feature_document["id"] = feature_document["properties"].pop("runid")
        unrelated = feature("unrelated")
        unrelated["id"] = unrelated["properties"].pop("runid")
        master["features"].append(unrelated)
        mapping = batch_mapping(descriptor)
        mapping[MASTER_URL] = sources.canonical_json(master)
        result, _ = self.prepare(descriptor, mapping)
        self.assertEqual(result.member_count, 2)

    def test_reviewed_property_map_binds_source_features_to_current_runids(self):
        descriptor = batch_descriptor()
        descriptor["master_identity"] = {
            "location": "properties-map",
            "property": "source_code",
            "mapping": {"N": "run-north", "S": "run-south"},
        }
        north = feature("historical-north")
        north["properties"]["source_code"] = "N"
        south = feature("historical-south", 0.2)
        south["properties"]["source_code"] = "S"
        mapping = batch_mapping(descriptor)
        mapping[MASTER_URL] = geojson(north, south)

        result, _ = self.prepare(descriptor, mapping)

        self.assertEqual(
            [member["runid"] for member in result.index["members"]],
            ["run-north", "run-south"],
        )
        for member in result.index["members"]:
            metadata = self.client.fetch(member["artifacts"]["metadata"]["sha256"])
            properties = json.loads(metadata.path.read_bytes())["source_properties"]
            self.assertEqual(properties["runid"], member["runid"])

    def test_reviewed_property_map_rejects_source_membership_drift(self):
        descriptor = batch_descriptor()
        descriptor["master_identity"] = {
            "location": "properties-map",
            "property": "source_code",
            "mapping": {"N": "run-north", "S": "run-south"},
        }
        north = feature("historical-north")
        north["properties"]["source_code"] = "N"
        mapping = batch_mapping(descriptor)
        mapping[MASTER_URL] = geojson(north)
        with self.assertRaises(sources.SourceMembershipError):
            self.prepare(descriptor, mapping)

        extra = feature("historical-extra")
        extra["properties"]["source_code"] = "X"
        mapping[MASTER_URL] = geojson(north, extra)
        with self.assertRaises(sources.SourceMembershipError):
            self.prepare(descriptor, mapping)

    def test_reviewed_property_map_accepts_only_explicit_exclusions(self):
        descriptor = batch_descriptor()
        descriptor["master_identity"] = {
            "location": "properties-map",
            "property": "source_code",
            "mapping": {"N": "run-north", "S": "run-south"},
            "excluded": ["X"],
        }
        documents = []
        for source_code, runid in (
            ("N", "historical-north"),
            ("S", "historical-south"),
            ("X", "historical-excluded"),
        ):
            document = feature(runid)
            document["properties"]["source_code"] = source_code
            documents.append(document)
        mapping = batch_mapping(descriptor)
        mapping[MASTER_URL] = geojson(*documents)

        result, _ = self.prepare(descriptor, mapping)

        self.assertEqual(result.member_count, 2)

    def test_standalone_publishes_one_exact_member(self):
        descriptor = standalone_descriptor()
        result, _ = self.prepare(descriptor, standalone_mapping(descriptor))
        member = result.index["members"][0]
        self.assertEqual(result.member_count, 1)
        self.assertEqual(result.source_count, 6)
        self.assertEqual(member["watershed_key"], "standalone")
        self.assertEqual(member["expected"]["subcatchments"], 1)
        self.assertEqual(member["expected"]["channels"], 1)

    def test_multipart_children_count_materialized_business_entities(self):
        descriptor = batch_descriptor()
        mapping = batch_mapping(descriptor)
        runid = descriptor["members"][0]["runid"]
        sub_url = descriptor["source_templates"]["subcatchments"].replace(
            "{runid}", runid
        )
        first = child_feature(runid, "subcatchments")
        second = child_feature(runid, "subcatchments", 0.01)
        mapping[sub_url] = geojson(first, second)

        result, _ = self.prepare(descriptor, mapping)

        self.assertEqual(result.index["members"][0]["expected"]["subcatchments"], 1)

    def test_empty_batch_result_is_fatal_before_index_publication(self):
        mapping = batch_mapping()
        mapping[MASTER_URL] = geojson()
        with self.assertRaises(sources.SourceFormatError):
            self.prepare(batch_descriptor(), mapping)
        self.assertFalse(any(path.name == "batch-member-index.json" for path in self.root.rglob("*")))

    def test_missing_extra_and_duplicate_batch_members_are_fatal(self):
        cases = {
            "missing": geojson(feature("run-north")),
            "extra": geojson(feature("run-north"), feature("run-south"), feature("run-extra")),
            "duplicate": geojson(feature("run-north"), feature("run-north")),
        }
        for label, master in cases.items():
            with self.subTest(label=label):
                mapping = batch_mapping()
                mapping[MASTER_URL] = master
                with self.assertRaises(sources.SourceMembershipError):
                    self.prepare(batch_descriptor(), mapping)

    def test_missing_required_source_is_fatal(self):
        mapping = batch_mapping()
        del mapping["https://source.example.test/runs/run-south/soils"]
        with self.assertRaises(sources.SourceFetchError):
            self.prepare(batch_descriptor(), mapping)

    def test_partial_download_is_integrity_failure(self):
        mapping = batch_mapping()
        mapping["https://source.example.test/runs/run-north/channels"] = sources.SourceIntegrityError(
            "source transfer ended before its declared length"
        )
        with self.assertRaises(sources.SourceIntegrityError):
            self.prepare(batch_descriptor(), mapping)

        class PartialResponse(io.BytesIO):
            headers = {"Content-Length": "20"}

        destination = self.root / "partial"
        with self.assertRaises(sources.SourceIntegrityError):
            sources._stream_response(PartialResponse(b"short"), destination, chunk_size=2)
        self.assertFalse(destination.exists())

    def test_malformed_geojson_and_parquet_are_fatal(self):
        mapping = batch_mapping()
        mapping["https://source.example.test/runs/run-north/subcatchments"] = b"not-json"
        with self.assertRaises(sources.SourceFormatError):
            self.prepare(batch_descriptor(), mapping)

        mapping = batch_mapping()
        mapping["https://source.example.test/runs/run-north/channels"] = (
            b'{"type":"FeatureCollection","features":[{"type":"Feature",'
            b'"properties":{"value":NaN},"geometry":{"type":"Point",'
            b'"coordinates":[-117,46]}}]}'
        )
        with self.assertRaises(sources.SourceFormatError):
            self.prepare(batch_descriptor(), mapping)

        mapping = batch_mapping()
        mapping["https://source.example.test/runs/run-north/hillslopes"] = b"not-parquet"
        with self.assertRaises(sources.SourceFormatError):
            self.prepare(batch_descriptor(), mapping)

    def test_authentication_value_is_used_but_never_persisted(self):
        descriptor = standalone_descriptor()
        descriptor["authentication"] = {"secret_ref": "DB17_FIXTURE_TOKEN"}
        fetcher = MappingFetcher(standalone_mapping(descriptor))
        with mock.patch.dict(os.environ, {"DB17_FIXTURE_TOKEN": "fixture-sensitive-value"}):
            result = sources.prepare_sources(
                descriptor,
                client=self.client,
                artifact_base_uri=ARTIFACT_BASE,
                fetcher=fetcher,
            )
        self.assertTrue(all(call[1]["Authorization"] == "Bearer fixture-sensitive-value" for call in fetcher.calls))
        persisted = result.index_bytes + result.receipt_bytes
        self.assertNotIn(b"fixture-sensitive-value", persisted)
        self.assertIn(b"DB17_FIXTURE_TOKEN", result.index_bytes)

        with mock.patch.dict(os.environ, {}, clear=True):
            replay = sources.prepare_sources(
                descriptor,
                client=self.client,
                artifact_base_uri=ARTIFACT_BASE,
                replay_receipt=result.receipt,
            )
        self.assertEqual(replay.index_bytes, result.index_bytes)

    def test_replay_rejects_descriptor_or_source_drift(self):
        descriptor = batch_descriptor()
        result, _ = self.prepare(descriptor, batch_mapping(descriptor))
        changed = json.loads(json.dumps(descriptor))
        changed["source_revision"] = "different"
        with self.assertRaises(sources.SourceIntegrityError):
            sources.prepare_sources(
                changed,
                client=self.client,
                artifact_base_uri=ARTIFACT_BASE,
                replay_receipt=result.receipt,
            )

        receipt = json.loads(json.dumps(result.receipt))
        receipt["sources"][0]["url"] = "https://source.example.test/changed"
        with self.assertRaises(sources.SourceIntegrityError):
            sources.prepare_sources(
                descriptor,
                client=self.client,
                artifact_base_uri=ARTIFACT_BASE,
                replay_receipt=receipt,
            )

    def test_source_document_credential_field_is_rejected(self):
        mapping = batch_mapping()
        bad = feature("run-north")
        bad["properties"]["api_token"] = "not-persisted"
        mapping[MASTER_URL] = geojson(bad, feature("run-south"))
        with self.assertRaises(sources.SourceFormatError):
            self.prepare(batch_descriptor(), mapping)


if __name__ == "__main__":
    unittest.main()
