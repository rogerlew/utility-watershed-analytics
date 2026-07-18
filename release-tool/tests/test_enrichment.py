from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from uwa_release_tool import artifacts, enrichment, sources  # noqa: E402


ARTIFACT_BASE = "https://artifacts.example.test/db18"
MASTER_URL = "https://source.example.test/nasa-202606/custom-master.geojson"
ENRICHMENT_URL = "https://source.example.test/WWS_Watersheds_HUC10_Merged.geojson"


def geometry(offset: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [-117.0 + offset, 46.0],
                [-116.9 + offset, 46.0],
                [-116.9 + offset, 46.1],
                [-117.0 + offset, 46.0],
            ]
        ],
    }


def target_feature(code: str, suffix: str, *, offset: float = 0.0) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "runid": f"{enrichment.TARGET_RUNID_PREFIX}{suffix}",
            "WWS_Code": code,
            "target_only": f"target-{suffix}",
        },
        "geometry": geometry(offset),
    }


def source_properties(code: str) -> dict:
    return {
        "PWS_ID": f"PWS-{code}",
        "SrcName": f"Source {code}",
        "PWS_Name": f"Utility {code}",
        "County_Nam": "Example County",
        "State": "OR",
        "HUC10_ID": f"HUC-{code}",
        "HUC10_Name": f"HUC {code}",
        "WWS_Code": code,
        "SrcType": "Public",
        "Shape_Leng": 12.5,
        "Shape_Area": 3.25,
        "outlet_lon_lat": [-116.95, 46.05],
        "runid": f"batch;;nasa-roses-2025;;{code}",
    }


def source_feature(code: str, *, offset: float = 2.0) -> dict:
    return {
        "type": "Feature",
        "properties": source_properties(code),
        "geometry": geometry(offset),
    }


def feature_collection(*features: dict) -> dict:
    return {"type": "FeatureCollection", "features": list(features)}


def parquet() -> bytes:
    metadata = b"db18-parquet"
    return b"PAR1" + metadata + len(metadata).to_bytes(4, "little") + b"PAR1"


class MappingFetcher:
    def __init__(self, mapping: dict[str, bytes]):
        self.mapping = mapping
        self.calls: list[str] = []

    def __call__(self, url: str, destination: Path, _headers: dict[str, str]) -> None:
        self.calls.append(url)
        destination.write_bytes(self.mapping[url])


def preparation_fixture() -> tuple[dict, dict[str, bytes]]:
    target = feature_collection(target_feature("A", "A"), target_feature("B", "B", offset=0.2))
    enrichment_source = feature_collection(source_feature("A"), source_feature("EXTRA"))
    enrichment_bytes = sources.canonical_json(enrichment_source)
    roles = ("subcatchments", "channels", "hillslopes", "soils", "landuse")
    descriptor = {
        "schema_version": 1,
        "kind": "batch",
        "collection_key": "nasa-roses",
        "source_revision": "nasa-202606-fixture",
        "created_at": "2026-07-17T12:00:00Z",
        "master_url": MASTER_URL,
        "source_templates": {
            role: f"https://source.example.test/runs/{{runid}}/{role}" for role in roles
        },
        "enrichment": {
            "type": "nasa-202606-wws-code",
            "source_url": ENRICHMENT_URL,
            "source_sha256": hashlib.sha256(enrichment_bytes).hexdigest(),
            "source_bytes": len(enrichment_bytes),
            "code_git_commit": "1" * 40,
            "validator_image_digest": f"sha256:{'2' * 64}",
        },
        "members": [
            {
                "watershed_key": "nasa-a",
                "runid": f"{enrichment.TARGET_RUNID_PREFIX}A",
                "display_name": "NASA A",
                "aliases": [],
            },
            {
                "watershed_key": "nasa-b",
                "runid": f"{enrichment.TARGET_RUNID_PREFIX}B",
                "display_name": "NASA B",
                "aliases": [],
            },
        ],
    }
    mapping = {
        MASTER_URL: sources.canonical_json(target),
        ENRICHMENT_URL: enrichment_bytes,
    }
    for member in descriptor["members"]:
        for role in roles:
            url = descriptor["source_templates"][role].replace("{runid}", member["runid"])
            mapping[url] = (
                sources.canonical_json(feature_collection(target_feature("A", "child")))
                if role in {"subcatchments", "channels"}
                else parquet()
            )
    return descriptor, mapping


class NasaEnrichmentTests(unittest.TestCase):
    def test_positive_join_is_deterministic_and_preserves_target_authority(self):
        target = feature_collection(
            target_feature("A", "A"),
            target_feature("B", "B", offset=0.2),
            target_feature("C", "C", offset=0.4),
        )
        target["features"][0]["properties"]["PWS_ID"] = "PWS-A"
        source = feature_collection(source_feature("A"), source_feature("B"), source_feature("EXTRA"))
        result = enrichment.enrich_nasa_202606(target, source)
        repeated = enrichment.enrich_nasa_202606(target, source)

        self.assertEqual((result.matched, result.target_unmatched, result.source_unmatched), (2, 1, 1))
        self.assertEqual((result.source_runid_differences, result.source_geometry_differences), (2, 2))
        self.assertEqual(sources.canonical_json(result.document), sources.canonical_json(repeated.document))
        for before, after in zip(target["features"], result.document["features"], strict=True):
            self.assertEqual(after["properties"]["runid"], before["properties"]["runid"])
            self.assertEqual(after["geometry"], before["geometry"])
            self.assertEqual(after["properties"]["target_only"], before["properties"]["target_only"])
        self.assertEqual(result.document["features"][0]["properties"]["SrcName"], "Source A")
        self.assertEqual(result.document["features"][1]["properties"]["PWS_ID"], "PWS-B")
        unmatched = result.document["features"][2]["properties"]
        self.assertEqual(unmatched["WWS_Code"], "C")
        self.assertTrue(all(unmatched[field] is None for field in enrichment.COPY_FIELDS if field != "WWS_Code"))
        self.assertNotEqual(
            result.document["features"][0]["properties"]["runid"],
            source["features"][0]["properties"]["runid"],
        )
        self.assertNotEqual(result.document["features"][0]["geometry"], source["features"][0]["geometry"])

    def test_missing_and_duplicate_join_keys_are_fatal(self):
        target = feature_collection(target_feature("A", "A"))
        source = feature_collection(source_feature("A"))
        for label, target_mutation, source_mutation in (
            ("missing-target", lambda value: value["features"][0]["properties"].pop("WWS_Code"), None),
            ("missing-source", None, lambda value: value["features"][0]["properties"].pop("WWS_Code")),
            ("null-target", lambda value: value["features"][0]["properties"].update(WWS_Code=None), None),
        ):
            with self.subTest(label=label):
                changed_target = copy.deepcopy(target)
                changed_source = copy.deepcopy(source)
                if target_mutation:
                    target_mutation(changed_target)
                if source_mutation:
                    source_mutation(changed_source)
                with self.assertRaisesRegex(enrichment.NasaEnrichmentError, "WWS_Code"):
                    enrichment.enrich_nasa_202606(changed_target, changed_source)

        with self.assertRaises(enrichment.NasaEnrichmentError) as target_error:
            enrichment.enrich_nasa_202606(
                feature_collection(target_feature("A", "A"), target_feature("A", "B")),
                source,
            )
        self.assertEqual(target_error.exception.code, "duplicate-join-key")
        self.assertEqual(target_error.exception.count, 1)
        with self.assertRaises(enrichment.NasaEnrichmentError) as source_error:
            enrichment.enrich_nasa_202606(
                target,
                feature_collection(source_feature("A"), source_feature("A")),
            )
        self.assertEqual(source_error.exception.code, "duplicate-join-key")

    def test_missing_source_field_conflict_and_wrong_prefix_are_fatal(self):
        target = feature_collection(target_feature("A", "A"))
        source = feature_collection(source_feature("A"))
        missing = copy.deepcopy(source)
        missing["features"][0]["properties"].pop("PWS_Name")
        with self.assertRaises(enrichment.NasaEnrichmentError) as missing_error:
            enrichment.enrich_nasa_202606(target, missing)
        self.assertEqual(missing_error.exception.code, "missing-source-field")

        conflict = copy.deepcopy(target)
        conflict["features"][0]["properties"]["PWS_ID"] = "different"
        with self.assertRaises(enrichment.NasaEnrichmentError) as conflict_error:
            enrichment.enrich_nasa_202606(conflict, source)
        self.assertEqual(conflict_error.exception.code, "conflicting-target-value")

        wrong_prefix = copy.deepcopy(target)
        wrong_prefix["features"][0]["properties"]["runid"] = "batch;;wrong;;A"
        with self.assertRaises(enrichment.NasaEnrichmentError) as prefix_error:
            enrichment.enrich_nasa_202606(wrong_prefix, source)
        self.assertEqual(prefix_error.exception.code, "invalid-target-runid")

    def test_preservation_validator_rejects_geometry_runid_count_and_property_changes(self):
        target = feature_collection(target_feature("A", "A"), target_feature("B", "B"))
        source = feature_collection(source_feature("A"), source_feature("B"))
        output = enrichment.enrich_nasa_202606(target, source).document
        mutations = {
            "geometry-changed": lambda value: value["features"][0].update(geometry=geometry(1.0)),
            "runid-changed": lambda value: value["features"][0]["properties"].update(runid="changed"),
            "member-count-changed": lambda value: value["features"].pop(),
            "target-property-changed": lambda value: value["features"][0]["properties"].update(target_only="changed"),
            "join-key-changed": lambda value: value["features"][0]["properties"].update(WWS_Code="changed"),
        }
        for expected_code, mutate in mutations.items():
            with self.subTest(expected_code=expected_code):
                changed = copy.deepcopy(output)
                mutate(changed)
                with self.assertRaises(enrichment.NasaEnrichmentError) as error:
                    enrichment.validate_preservation(target, changed)
                self.assertEqual(error.exception.code, expected_code)

    def test_lineage_decisions_are_fixed_and_unique(self):
        decisions = enrichment.lineage_field_decisions("1" * 64, "2" * 64)
        fields = [decision["field"] for decision in decisions]
        self.assertEqual(len(fields), 14)
        self.assertEqual(len(fields), len(set(fields)))
        self.assertEqual(next(item for item in decisions if item["field"] == "runid")["authority"], "target")
        self.assertEqual(next(item for item in decisions if item["field"] == "wws_code")["authority"], "target")
        self.assertEqual(next(item for item in decisions if item["field"] == "pws_id")["authority"], "source")


class NasaPreparationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.client = artifacts.ArtifactClient(self.root / "store", self.root / "cache")

    def tearDown(self):
        self.temporary.cleanup()

    def artifact_json(self, reference: dict) -> dict:
        digest = reference["sha256"]
        return json.loads(self.client.fetch(digest).path.read_bytes())

    def test_preparation_publishes_output_report_lineage_and_exact_replay(self):
        descriptor, mapping = preparation_fixture()
        fetcher = MappingFetcher(mapping)
        result = sources.prepare_sources(
            descriptor,
            client=self.client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=fetcher,
        )
        self.assertEqual(result.source_count, 12)
        lineage_references = [member["transformation_lineage"] for member in result.index["members"]]
        self.assertEqual(lineage_references[0], lineage_references[1])
        lineage = self.artifact_json(lineage_references[0])
        self.assertEqual(lineage["join_keys"], ["WWS_Code"])
        self.assertEqual(lineage["counts"], {"matched": 1, "unmatched": 2, "duplicate": 0})
        report = self.artifact_json(lineage["validation_report"])
        checks = {check["code"]: check["count"] for check in report["checks"]}
        self.assertEqual(checks["target-unmatched"], 1)
        self.assertEqual(checks["source-unmatched"], 1)
        self.assertEqual(checks["source-runids-ignored"], 2)
        self.assertEqual(checks["source-runid-differences"], 1)
        self.assertEqual(checks["source-geometry-differences"], 1)
        enriched = self.artifact_json(lineage["output"])
        self.assertEqual(enriched["features"][0]["properties"]["PWS_ID"], "PWS-A")
        self.assertIsNone(enriched["features"][1]["properties"]["PWS_ID"])
        metadata = self.artifact_json(result.index["members"][0]["artifacts"]["metadata"])
        self.assertEqual(metadata["source_properties"]["PWS_ID"], "PWS-A")
        self.assertNotIn("batch;;nasa-roses-2025", json.dumps(enriched))

        def upstream_forbidden(_url: str, _path: Path, _headers: dict[str, str]) -> None:
            raise AssertionError("replay called upstream")

        replay = sources.prepare_sources(
            descriptor,
            client=self.client,
            artifact_base_uri=ARTIFACT_BASE,
            fetcher=upstream_forbidden,
            replay_receipt=result.receipt,
        )
        self.assertEqual(replay.index_bytes, result.index_bytes)
        self.assertEqual(replay.receipt_bytes, result.receipt_bytes)

    def test_source_size_and_checksum_mismatch_fail_before_index(self):
        descriptor, mapping = preparation_fixture()
        changed_size = copy.deepcopy(descriptor)
        changed_size["enrichment"]["source_bytes"] += 1
        with self.assertRaises(sources.SourceIntegrityError):
            sources.prepare_sources(
                changed_size,
                client=self.client,
                artifact_base_uri=ARTIFACT_BASE,
                fetcher=MappingFetcher(mapping),
            )

        changed_hash = copy.deepcopy(descriptor)
        changed_hash["enrichment"]["source_sha256"] = "0" * 64
        with self.assertRaises(sources.SourceIntegrityError):
            sources.prepare_sources(
                changed_hash,
                client=self.client,
                artifact_base_uri=ARTIFACT_BASE,
                fetcher=MappingFetcher(mapping),
            )


if __name__ == "__main__":
    unittest.main()
