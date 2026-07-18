import hashlib
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from server.watershed.models import (
    ActiveDataRelease,
    DataRelease,
    DataRunState,
    RunCapability,
    Watershed,
    WatershedCollection,
    WatershedIdentity,
)
from server.watershed.runtime_capabilities import resolve_capability
from server.watershed.rhessys_outputs.query import execute_materialized_query


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def artifact(base_uri, name, media_type):
    return {
        "uri": f"{base_uri}{name}",
        "sha256": digest(name),
        "bytes": 10,
        "media_type": media_type,
        "verified": True,
    }


def rhessys_configuration(base_uri, index_uri, index_sha256, *, enabled=True):
    geometry_revision = digest("geometry")
    variable = {"id": "flow", "label": "Flow", "units": "mm/day"}
    return {
        "schema_version": 1,
        "enabled": enabled,
        "access_policy": "public" if enabled else "disabled",
        "index_uri": index_uri,
        "index_sha256": index_sha256,
        "geometry_revision": geometry_revision,
        "scenarios": [
            {
                "id": "S1",
                "label": "Baseline",
                "description": "A public synthetic baseline.",
                "is_change": False,
                "variables": ["flow"],
                "year_range": [2000, 2001],
                "geometry_revision": geometry_revision,
            }
        ],
        "variables": [variable],
        "spatial_inputs": [
            {
                "filename": "slope.tif",
                "title": "Slope",
                "artifact": artifact(base_uri, "slope.tif", "image/tiff"),
                "render": {
                    "type": "continuous",
                    "min": 0,
                    "max": 10,
                    "unique_values": None,
                    "group": "terrain",
                    "reversed": False,
                },
                "geometry_revision": geometry_revision,
            }
        ],
        "geotiffs": [
            {
                "scenario": "S1",
                "variable": "flow",
                "artifact": artifact(base_uri, "flow.tif", "image/tiff"),
                "value_range": {"min": 1, "max": 9},
                "geometry_revision": geometry_revision,
            }
        ],
        "parquets": [
            {
                "dataset_key": role,
                "scenario": "S1",
                "role": role,
                "artifact": artifact(
                    base_uri,
                    f"{role}.parquet",
                    "application/vnd.apache.parquet",
                ),
                "spatial_id_field": "hillID" if role == "hillslope" else "basinID",
                "variables": [variable],
                "year_range": [2000, 2001],
                "geometry_revision": geometry_revision,
            }
            for role in ("hillslope", "basin")
        ],
        "geometries": [
            {
                "scale": "hillslope",
                "scenarios": ["S1"],
                "artifact": artifact(
                    base_uri,
                    "hillslope.geojson",
                    "application/geo+json",
                ),
                "source_crs": "EPSG:4326",
                "geometry_revision": geometry_revision,
            }
        ],
    }


class RuntimeCapabilityTests(TestCase):
    runid = "aversive-forestry"

    def setUp(self):
        self.client = APIClient()
        self.collection = WatershedCollection.objects.create(key="runtime-test")
        self.identity = WatershedIdentity.objects.create(
            watershed_key="runtime-test",
            collection=self.collection,
        )
        self.release = DataRelease.objects.create(
            release_id="2026-07-18.1",
            manifest_sha256=digest("manifest"),
            release_fingerprint=digest("release"),
            domain_fingerprint=digest("domain"),
            supported_migration="watershed.0011_capability_runtime_types",
            materializer_image_digest=f"sha256:{digest('image')}",
            materializer_git_commit=digest("commit")[:40],
            expected_watersheds=1,
            expected_subcatchments=0,
            expected_channels=0,
            actual_watersheds=1,
            actual_subcatchments=0,
            actual_channels=0,
            validation_summary={"status": "passed"},
            created_at=timezone.now(),
        )
        self.run_state = DataRunState.objects.create(
            release=self.release,
            collection=self.collection,
            watershed_identity=self.identity,
            runid=self.runid,
            run_fingerprint=digest("run"),
            metadata_fingerprint=digest("metadata"),
            geometry_fingerprint=digest("run-geometry"),
            subcatchment_fingerprint=digest("subcatchment"),
            channel_fingerprint=digest("channel"),
            hillslope_fingerprint=digest("hillslope"),
            soil_fingerprint=digest("soil"),
            landuse_fingerprint=digest("landuse"),
            transformation_lineage_fingerprint=digest("transform"),
            capability_fingerprint=digest("capability"),
            actual_subcatchments=0,
            actual_channels=0,
        )

    def create_rhessys(self, *, enabled=True, run_state=None):
        base_uri = "https://artifacts.example.test/release/run/rhessys/"
        index_uri = f"{base_uri}index.json"
        index_sha256 = digest("rhessys-index")
        return RunCapability.objects.create(
            run_state=run_state or self.run_state,
            watershed_identity=self.identity,
            capability_type=RunCapability.CapabilityType.RHESSYS,
            mode=RunCapability.Mode.BOTH,
            durable_base_uri=base_uri,
            index_uri=index_uri,
            index_sha256=index_sha256,
            capability_fingerprint=digest("capability"),
            runtime_configuration=rhessys_configuration(
                base_uri,
                index_uri,
                index_sha256,
                enabled=enabled,
            ),
        )

    def create_sbs(self):
        base_uri = "https://artifacts.example.test/release/run/sbs/"
        index_uri = f"{base_uri}index.json"
        index_sha256 = digest("sbs-index")
        return RunCapability.objects.create(
            run_state=self.run_state,
            watershed_identity=self.identity,
            capability_type=RunCapability.CapabilityType.SBS,
            mode=RunCapability.Mode.PRECOMPUTED,
            durable_base_uri=base_uri,
            index_uri=index_uri,
            index_sha256=index_sha256,
            capability_fingerprint=digest("capability"),
            runtime_configuration={
                "schema_version": 1,
                "enabled": True,
                "access_policy": "public",
                "index_uri": index_uri,
                "index_sha256": index_sha256,
                "geometry_revision": digest("sbs-geometry"),
                "artifact": artifact(base_uri, "sbs.tif", "image/tiff"),
            },
        )

    def activate(self):
        ActiveDataRelease.objects.filter(singleton_id=1).update(
            state=ActiveDataRelease.State.ACTIVE,
            release=self.release,
            manifest_sha256=self.release.manifest_sha256,
            data_contract=self.release.data_contract,
            activated_at=timezone.now(),
        )

    def create_watershed(self, runid="sbs-run"):
        return Watershed.objects.create(
            runid=runid,
            geom=GEOSGeometry(
                "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
                srid=4326,
            ),
        )

    def test_empty_fallback_is_exact_and_observable(self):
        with self.assertLogs("watershed.runtime_capabilities", "INFO") as logs:
            capability = resolve_capability(
                self.runid,
                RunCapability.CapabilityType.RHESSYS,
            )
        self.assertTrue(capability.available)
        self.assertEqual(capability.source, "legacy-empty")
        self.assertIn("capability.legacy_fallback", logs.output[0])

        unknown = resolve_capability(
            "not-allowlisted",
            RunCapability.CapabilityType.RHESSYS,
        )
        self.assertFalse(unknown.available)
        self.assertEqual(unknown.source, "none")

    def test_empty_sbs_requires_an_existing_watershed(self):
        missing = resolve_capability("sbs-run", RunCapability.CapabilityType.SBS)
        self.assertFalse(missing.available)
        self.create_watershed()
        with self.assertLogs("watershed.runtime_capabilities", "INFO"):
            available = resolve_capability(
                "sbs-run",
                RunCapability.CapabilityType.SBS,
            )
        self.assertTrue(available.available)
        self.assertEqual(available.source, "legacy-empty")

    def test_empty_routes_cannot_bypass_declared_legacy_mode(self):
        precomputed_run = "batch;;victoria-ca-2026-sbs;;Sooke09"
        with (
            patch(
                "server.watershed.rhessys_outputs.views.get_map_download_url"
            ) as output_url,
            patch(
                "server.watershed.rhessys_spatial.views.discover_spatial_inputs"
            ) as spatial_discovery,
            patch(
                "server.watershed.rhessys_outputs.views.resolve_run_base_url"
            ) as geometry_base,
        ):
            dynamic_output = self.client.get(
                reverse(
                    "rhessys-outputs-tile",
                    args=[self.runid, "S1", "flow", 1, 2, 3],
                )
            )
            precomputed_spatial = self.client.get(
                reverse("rhessys-spatial-list", args=[precomputed_run])
            )
            precomputed_geometry = self.client.get(
                reverse(
                    "rhessys-outputs-geometry",
                    args=[precomputed_run, "hillslope"],
                )
            )
        self.assertEqual(dynamic_output.status_code, 404)
        self.assertEqual(precomputed_spatial.status_code, 200)
        self.assertEqual(precomputed_spatial.data["files"], [])
        self.assertEqual(precomputed_geometry.status_code, 404)
        output_url.assert_not_called()
        spatial_discovery.assert_not_called()
        geometry_base.assert_not_called()

    def test_active_transition_atomically_disables_all_fallback(self):
        self.assertTrue(
            resolve_capability(
                self.runid,
                RunCapability.CapabilityType.RHESSYS,
            ).available
        )
        self.activate()
        capability = resolve_capability(
            self.runid,
            RunCapability.CapabilityType.RHESSYS,
        )
        self.assertFalse(capability.available)
        self.assertEqual(capability.source, "none")

    def test_active_uses_only_exact_valid_public_capability(self):
        row = self.create_rhessys()
        self.activate()
        capability = resolve_capability(
            self.runid,
            RunCapability.CapabilityType.RHESSYS,
        )
        self.assertTrue(capability.available)
        self.assertEqual(capability.source, "materialized")
        self.assertEqual(capability.index_uri, row.index_uri)
        self.assertEqual(capability.configuration["variables"][0]["id"], "flow")

    def test_active_disabled_or_malformed_capability_fails_closed(self):
        row = self.create_rhessys(enabled=False)
        self.activate()
        disabled = resolve_capability(
            self.runid,
            RunCapability.CapabilityType.RHESSYS,
        )
        self.assertFalse(disabled.available)
        self.assertIsNone(disabled.configuration)

        RunCapability.objects.filter(pk=row.pk).update(
            runtime_configuration={"enabled": True}
        )
        malformed = resolve_capability(
            self.runid,
            RunCapability.CapabilityType.RHESSYS,
        )
        self.assertFalse(malformed.available)
        self.assertEqual(malformed.source, "invalid")

    @patch("server.watershed.rhessys_outputs.views.discover_output_maps")
    def test_active_catalog_uses_declared_metadata_without_discovery(self, discover):
        self.create_rhessys()
        self.activate()
        response = self.client.get(
            reverse("rhessys-outputs-list", args=[self.runid])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scenarios"][0]["id"], "S1")
        self.assertEqual(
            response.data["variables"][0]["spatial_scales"],
            ["hillslope"],
        )
        self.assertEqual(response.data["capability"]["source"], "materialized")
        discover.assert_not_called()

    @patch("server.watershed.rhessys_outputs.views.execute_legacy_query")
    @patch("server.watershed.rhessys_outputs.views.execute_materialized_query")
    def test_active_query_selects_materialized_executor(self, materialized, legacy):
        self.create_rhessys()
        self.activate()
        materialized.return_value = [{"spatialId": 1, "value": 2.0}]
        response = self.client.post(
            reverse("rhessys-query", args=[self.runid]),
            {
                "kind": "choropleth",
                "scenario": "S1",
                "variable": "flow",
                "spatial_scale": "hillslope",
                "year": 2000,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        materialized.assert_called_once()
        legacy.assert_not_called()

    def test_materialized_query_reads_only_declared_checksum_verified_parquet(self):
        self.create_rhessys()
        self.activate()
        capability = resolve_capability(
            self.runid,
            RunCapability.CapabilityType.RHESSYS,
        )
        sink = pa.BufferOutputStream()
        pq.write_table(
            pa.table(
                {
                    "year": [2000, 2000, 2001],
                    "hillID": [1, 1, 2],
                    "flow": [2.0, 4.0, 8.0],
                }
            ),
            sink,
        )
        with patch(
            "server.watershed.rhessys_outputs.query.fetch_verified_artifact",
            return_value=sink.getvalue().to_pybytes(),
        ) as fetch_artifact:
            rows = execute_materialized_query(
                capability,
                {
                    "kind": "choropleth",
                    "scenario": "S1",
                    "variable": "flow",
                    "spatial_scale": "hillslope",
                    "year": 2000,
                },
            )
        self.assertEqual(rows, [{"spatialId": 1, "value": 3.0}])
        fetch_artifact.assert_called_once_with(
            capability.configuration["parquets"][0]["artifact"]
        )

    def test_active_raster_routes_use_only_declared_artifact_uris(self):
        row = self.create_rhessys()
        sbs_row = self.create_sbs()
        self.activate()
        rhessys = row.runtime_configuration
        with (
            patch(
                "server.watershed.rhessys_outputs.views.get_tile_png",
                return_value=b"png",
            ) as output_tile,
            patch(
                "server.watershed.rhessys_outputs.views.get_map_download_url"
            ) as legacy_output,
            patch(
                "server.watershed.rhessys_spatial.views.get_tile_png",
                return_value=b"png",
            ) as spatial_tile,
            patch(
                "server.watershed.rhessys_spatial.views.get_download_url"
            ) as legacy_spatial,
            patch(
                "server.watershed.sbs_raster.views.get_tile_png",
                return_value=b"png",
            ) as sbs_tile,
            patch(
                "server.watershed.sbs_raster.views.resolve_run_base_url"
            ) as legacy_sbs,
        ):
            output_response = self.client.get(
                reverse(
                    "rhessys-outputs-tile",
                    args=[self.runid, "S1", "flow", 1, 2, 3],
                )
            )
            spatial_response = self.client.get(
                reverse(
                    "rhessys-spatial-tile",
                    args=[self.runid, "slope.tif", 1, 2, 3],
                )
            )
            sbs_response = self.client.get(
                reverse("sbs-tile", args=[self.runid, 1, 2, 3])
            )
        self.assertEqual(output_response.status_code, 200)
        self.assertEqual(spatial_response.status_code, 200)
        self.assertEqual(sbs_response.status_code, 200)
        output_tile.assert_called_once_with(
            rhessys["geotiffs"][0]["artifact"]["uri"],
            1,
            2,
            3,
            is_change=False,
        )
        self.assertEqual(
            spatial_tile.call_args.args[0],
            rhessys["spatial_inputs"][0]["artifact"]["uri"],
        )
        self.assertEqual(
            sbs_tile.call_args.args[0],
            sbs_row.runtime_configuration["artifact"]["uri"],
        )
        legacy_output.assert_not_called()
        legacy_spatial.assert_not_called()
        legacy_sbs.assert_not_called()

    def test_active_geometry_uses_declared_verified_artifact(self):
        row = self.create_rhessys()
        self.activate()
        geometry = row.runtime_configuration["geometries"][0]
        document = b'{"type":"FeatureCollection","features":[]}'
        with (
            patch(
                "server.watershed.rhessys_outputs.views.fetch_verified_artifact",
                return_value=document,
            ) as fetch_artifact,
            patch(
                "server.watershed.rhessys_outputs.views.resolve_run_base_url"
            ) as legacy_base,
        ):
            response = self.client.get(
                reverse(
                    "rhessys-outputs-geometry",
                    args=[self.runid, "hillslope"],
                ),
                {"scenario": "S1"},
            )
        self.assertEqual(response.status_code, 200)
        fetch_artifact.assert_called_once_with(geometry["artifact"])
        legacy_base.assert_not_called()

    @patch("server.watershed.sbs_raster.views.resolve_run_base_url")
    @patch("server.watershed.sbs_raster.views.fetch_verified_artifact")
    def test_active_sbs_download_uses_declared_verified_artifact(
        self,
        fetch_artifact,
        legacy_base,
    ):
        row = self.create_sbs()
        self.activate()
        fetch_artifact.return_value = b"synthetic-tiff"
        response = self.client.get(
            reverse("sbs-download", args=[self.runid])
        )
        self.assertEqual(response.status_code, 200)
        fetch_artifact.assert_called_once_with(
            row.runtime_configuration["artifact"]
        )
        legacy_base.assert_not_called()

    def test_capability_endpoint_exposes_sanitized_runtime_metadata(self):
        self.create_rhessys()
        self.create_sbs()
        self.activate()
        response = self.client.get(
            reverse("watershed-capabilities", args=[self.runid])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], "ACTIVE")
        self.assertTrue(response.data["rhessys"]["available"])
        self.assertTrue(response.data["sbs"]["available"])
        self.assertEqual(response.data["rhessys"]["scenarios"][0]["id"], "S1")
        self.assertNotIn("runtime_configuration", response.data["rhessys"])
        self.assertNotIn("uri", response.data["sbs"])
