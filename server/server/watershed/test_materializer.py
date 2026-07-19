import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pyarrow as arrow
import pyarrow.parquet as parquet
from django.test import TestCase
from django.utils import timezone

from server.watershed.materializer import (
    CapabilityDeclaration,
    MaterializationError,
    MaterializationMember,
    _child_records,
    build_and_activate_empty_release,
    stage_locked_release,
)
from server.watershed.models import (
    ActiveDataRelease,
    Channel,
    DataArtifactLineage,
    DataRelease,
    DataReleaseAttempt,
    DataRunState,
    RunCapability,
    Subcatchment,
    Watershed,
    WatershedCollection,
    WatershedIdentity,
    WatershedRunAlias,
)
from server.watershed.release_ledger import begin_release_attempt, transition_attempt
from server.watershed.staging import SpaceBudget
from server.watershed.staging_models import (
    DataReleaseStagingState,
    StagedChannel,
    StagedRunCapability,
    StagedSubcatchment,
    StagedWatershed,
)


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def polygon(offset):
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [offset, 0],
                [offset + 0.8, 0],
                [offset + 0.8, 0.8],
                [offset, 0.8],
                [offset, 0],
            ]
        ],
    }


class MaterializerFixtureMixin:
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_json(self, name, document):
        path = self.root / name
        path.write_text(
            json.dumps(document, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        return path

    def _write_parquet(self, name, values, column, *, topazids=(1, 2)):
        path = self.root / name
        parquet.write_table(
            arrow.table({"TopazID": list(topazids), column: list(values)}),
            path,
        )
        return path

    def _lineage(self, run_state, role, path, media_type, *, base_uri=None):
        content = path.read_bytes()
        artifact_digest = hashlib.sha256(content).hexdigest()
        base_uri = base_uri or f"https://artifacts.example.test/{run_state.runid}/"
        return DataArtifactLineage.objects.create(
            run_state=run_state,
            role=role,
            uri=f"{base_uri}{path.name}",
            sha256=artifact_digest,
            byte_size=len(content),
            media_type=media_type,
        )

    def _member(self, run_state, *, source_kind, capability=False, invalid=False):
        run_slug = run_state.runid.replace("/", "-")
        metadata = self._write_json(
            f"{run_slug}-metadata.json",
            {
                "schema_version": 1,
                "collection_key": run_state.collection_id,
                "source_revision": f"{source_kind}-revision",
                "watershed_key": run_state.watershed_identity.watershed_key,
                "runid": run_state.runid,
                "display_name": f"{source_kind.title()} watershed",
                "aliases": [],
                "source_properties": {
                    "State": "WA",
                    "SrcName": f"{source_kind.title()} source",
                },
            },
        )
        boundary = self._write_json(
            f"{run_slug}-boundary.geojson",
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": polygon(0),
                    }
                ],
            },
        )
        subcatchments = self._write_json(
            f"{run_slug}-subcatchments.geojson",
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"TopazID": topazid, "WeppID": topazid + 100},
                        "geometry": polygon(topazid),
                    }
                    for topazid in (1, 2)
                ],
            },
        )
        channels = self._write_json(
            f"{run_slug}-channels.geojson",
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"TopazID": 1, "WeppID": 201, "Order": 1},
                        "geometry": polygon(3),
                    }
                ],
            },
        )
        hillslopes = self._write_parquet(
            f"{run_slug}-hillslopes.parquet", (0.1, 0.2), "slope_scalar"
        )
        soils = self._write_parquet(
            f"{run_slug}-soils.parquet", ("101", "102"), "mukey"
        )
        landuse = self._write_parquet(
            f"{run_slug}-landuse.parquet", (7, 8), "key"
        )
        files = {
            "metadata": (metadata, "application/json"),
            "boundary": (boundary, "application/geo+json"),
            "subcatchments": (subcatchments, "application/geo+json"),
            "channels": (channels, "application/geo+json"),
            "hillslopes": (hillslopes, "application/vnd.apache.parquet"),
            "soils": (soils, "application/vnd.apache.parquet"),
            "landuse": (landuse, "application/vnd.apache.parquet"),
        }
        capability_declaration = None
        if capability:
            base_uri = f"https://artifacts.example.test/{run_slug}/sbs/"
            index = self._write_json(
                f"{run_slug}-sbs-index.json",
                {"schema_version": 1, "kind": "synthetic-sbs"},
            )
            index_lineage = self._lineage(
                run_state,
                "sbs-index",
                index,
                "application/json",
                base_uri=base_uri,
            )
            files["sbs-index"] = (index, "application/json")
            artifact_uri = f"{base_uri}sbs.tif"
            capability_declaration = CapabilityDeclaration(
                capability_type=RunCapability.CapabilityType.SBS,
                mode=RunCapability.Mode.PRECOMPUTED,
                durable_base_uri=base_uri,
                index_role="sbs-index",
                runtime_configuration={
                    "schema_version": 1,
                    "enabled": True,
                    "access_policy": "unsupported" if invalid else "public",
                    "index_uri": index_lineage.uri,
                    "index_sha256": index_lineage.sha256,
                    "geometry_revision": digest("sbs-geometry"),
                    "artifact": {
                        "uri": artifact_uri,
                        "sha256": digest("sbs-artifact"),
                        "bytes": 4096,
                        "media_type": "image/tiff",
                        "verified": True,
                    },
                },
            )
        paths = {}
        for role, (path, media_type) in files.items():
            paths[role] = path
            if role != "sbs-index":
                self._lineage(run_state, role, path, media_type)
        return MaterializationMember(
            run_state=run_state,
            artifact_paths=paths,
            capability=capability_declaration,
        )

    def _release(
        self,
        *,
        invalid_capability=False,
        runid_format="{source}/run-{index}",
    ):
        release = DataRelease.objects.create(
            release_id="2026-07-18.20",
            manifest_sha256=digest("db20-manifest"),
            release_fingerprint=digest("db20-release"),
            domain_fingerprint=digest("db20-domain"),
            supported_migration="watershed.0011_capability_runtime_types",
            materializer_image_digest=f"sha256:{digest('db20-image')}",
            materializer_git_commit=digest("db20-commit")[:40],
            expected_watersheds=2,
            expected_subcatchments=4,
            expected_channels=2,
            actual_watersheds=2,
            actual_subcatchments=4,
            actual_channels=2,
            validation_summary={"status": "passed"},
            created_at=timezone.now(),
        )
        members = []
        for index, source_kind in enumerate(("batch", "standalone"), start=1):
            collection = WatershedCollection.objects.create(
                key=f"db20-{source_kind}-collection"
            )
            identity = WatershedIdentity.objects.create(
                watershed_key=f"db20-{source_kind}-watershed",
                collection=collection,
            )
            capability_fingerprint = (
                digest("db20-sbs-capability") if index == 2 else None
            )
            run_state = DataRunState.objects.create(
                release=release,
                collection=collection,
                watershed_identity=identity,
                runid=runid_format.format(source=source_kind, index=index),
                run_fingerprint=digest(f"run-{index}"),
                metadata_fingerprint=digest(f"metadata-{index}"),
                geometry_fingerprint=digest(f"geometry-{index}"),
                subcatchment_fingerprint=digest(f"subcatchment-{index}"),
                channel_fingerprint=digest(f"channel-{index}"),
                hillslope_fingerprint=digest(f"hillslope-{index}"),
                soil_fingerprint=digest(f"soil-{index}"),
                landuse_fingerprint=digest(f"landuse-{index}"),
                capability_fingerprint=capability_fingerprint,
                actual_subcatchments=2,
                actual_channels=1,
            )
            WatershedRunAlias.objects.create(
                runid=run_state.runid,
                watershed_identity=identity,
                is_current=True,
            )
            members.append(
                self._member(
                    run_state,
                    source_kind=source_kind,
                    capability=index == 2,
                    invalid=invalid_capability and index == 2,
                )
            )
        return release, members

    def _attempt(self, release):
        attempt = begin_release_attempt(
            release=release,
            actor_kind=DataReleaseAttempt.ActorKind.OPERATOR,
            actor_identifier="db20-test",
            target_environment="test",
            application_git_commit=digest("application")[:40],
            reviewed_plan_sha256=digest("db20-plan"),
            lease_owner=f"forest1:{release.release_id}",
        )
        return transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)

    def _budget(self, members):
        artifact_bytes = sum(
            path.stat().st_size
            for member in members
            for path in member.artifact_paths.values()
        )
        return SpaceBudget(
            artifact_bytes=artifact_bytes,
            staging_bytes=1024,
            index_bytes=1024,
            backup_bytes=1024,
            wal_bytes=1024,
            margin_bytes=1024,
        )


class StrictEmptyMaterializerTests(MaterializerFixtureMixin, TestCase):

    def test_multipart_subcatchment_features_merge_by_business_identity(self):
        path = self._write_json(
            "multipart-subcatchments.geojson",
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"TopazID": 1, "WeppID": 101},
                        "geometry": polygon(offset),
                    }
                    for offset in (1, 3)
                ],
            },
        )
        artifact = SimpleNamespace(
            path=path,
            lineage=SimpleNamespace(role="subcatchments"),
            assert_unchanged=lambda: None,
        )
        member = SimpleNamespace(run_state=SimpleNamespace(
            watershed_identity=SimpleNamespace(),
            subcatchment_fingerprint=digest("subcatchments"),
        ))

        records = list(_child_records(member, artifact, model=StagedSubcatchment))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["topazid"], 1)
        self.assertEqual(len(records[0]["geom"]), 2)

    def test_multi_run_mixed_source_build_is_exact_and_bounded(self):
        release, members = self._release()
        attempt = self._attempt(release)
        budget = self._budget(members)
        result = build_and_activate_empty_release(
            attempt,
            members,
            budget=budget,
            observed_available_bytes=budget.required_bytes,
            actual_plan_sha256=attempt.reviewed_plan_sha256,
            batch_size=1,
        )

        attempt.refresh_from_db()
        active = ActiveDataRelease.objects.get(singleton_id=1)
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.SUCCEEDED)
        self.assertEqual(active.release, release)
        self.assertEqual((Watershed.objects.count(), Subcatchment.objects.count()), (2, 4))
        self.assertEqual(Channel.objects.count(), 2)
        self.assertEqual(RunCapability.objects.count(), 1)
        self.assertLessEqual(result.staging.maximum_batch_rows, 1)
        self.assertLessEqual(result.applied.maximum_batch_rows, 1)
        standalone = Watershed.objects.get(runid="standalone/run-2")
        self.assertEqual(standalone.srcname, "Standalone source")
        self.assertEqual(standalone.state, "WA")
        child = Subcatchment.objects.get(
            watershed_id="batch/run-1",
            topazid=2,
        )
        self.assertEqual(child.weppid, 102)
        self.assertEqual(child.slope_scalar, 0.2)
        self.assertEqual(child.mukey, "102")
        self.assertEqual(child.landuse_key, 8)

    def test_same_locked_inputs_produce_same_canonical_staging(self):
        release, members = self._release()
        budget = self._budget(members)

        def stage_snapshot():
            attempt = self._attempt(release)
            stage_locked_release(
                attempt,
                members,
                budget=budget,
                observed_available_bytes=budget.required_bytes,
                batch_size=1,
            )
            snapshot = {
                "watersheds": list(
                    StagedWatershed.objects.filter(attempt=attempt)
                    .order_by("runid")
                    .values_list("runid", "metadata", "source_fingerprint")
                ),
                "subcatchments": list(
                    StagedSubcatchment.objects.filter(attempt=attempt)
                    .order_by("run_state__runid", "topazid")
                    .values_list("run_state__runid", "topazid", "weppid", "attributes")
                ),
                "channels": list(
                    StagedChannel.objects.filter(attempt=attempt)
                    .order_by("run_state__runid", "topazid")
                    .values_list("run_state__runid", "topazid", "weppid", "order")
                ),
                "capabilities": list(
                    StagedRunCapability.objects.filter(attempt=attempt)
                    .order_by("run_state__runid")
                    .values_list(
                        "run_state__runid",
                        "capability_type",
                        "mode",
                        "index_sha256",
                        "runtime_configuration",
                    )
                ),
            }
            transition_attempt(
                attempt,
                DataReleaseAttempt.Status.FAILED,
                failure_phase="test-reset",
                failure_summary="canonical replay",
            )
            return snapshot

        self.assertEqual(stage_snapshot(), stage_snapshot())

    def test_late_capability_failure_rolls_back_entire_empty_build(self):
        release, members = self._release(invalid_capability=True)
        attempt = self._attempt(release)
        budget = self._budget(members)
        with self.assertRaisesRegex(MaterializationError, "access policy"):
            build_and_activate_empty_release(
                attempt,
                members,
                budget=budget,
                observed_available_bytes=budget.required_bytes,
                actual_plan_sha256=attempt.reviewed_plan_sha256,
                batch_size=1,
            )

        attempt.refresh_from_db()
        active = ActiveDataRelease.objects.get(singleton_id=1)
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.FAILED)
        self.assertEqual(active.state, ActiveDataRelease.State.EMPTY)
        self.assertEqual(Watershed.objects.count(), 0)
        self.assertEqual(Subcatchment.objects.count(), 0)
        self.assertEqual(Channel.objects.count(), 0)
        self.assertEqual(RunCapability.objects.count(), 0)
        self.assertEqual(
            DataReleaseStagingState.objects.get(attempt=attempt).status,
            DataReleaseStagingState.Status.READY,
        )

    def test_bad_required_parquet_keeps_serving_base_empty(self):
        release, members = self._release()
        bad_member = members[0]
        bad_path = bad_member.artifact_paths["soils"]
        parquet.write_table(
            arrow.table({"TopazID": [1, 1], "mukey": ["101", "duplicate"]}),
            bad_path,
        )
        lineage = DataArtifactLineage.objects.get(
            run_state=bad_member.run_state,
            role="soils",
        )
        content = bad_path.read_bytes()
        DataArtifactLineage.objects.filter(pk=lineage.pk).update(
            sha256=hashlib.sha256(content).hexdigest(),
            byte_size=len(content),
        )
        attempt = self._attempt(release)
        budget = self._budget(members)
        with self.assertRaisesRegex(MaterializationError, "strictly increasing"):
            stage_locked_release(
                attempt,
                members,
                budget=budget,
                observed_available_bytes=budget.required_bytes,
                batch_size=1,
            )

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.FAILED)
        self.assertGreater(StagedSubcatchment.objects.filter(attempt=attempt).count(), 0)
        self.assertEqual(Watershed.objects.count(), 0)
        self.assertEqual(Subcatchment.objects.count(), 0)
        self.assertEqual(Channel.objects.count(), 0)
        self.assertEqual(
            ActiveDataRelease.objects.get(singleton_id=1).state,
            ActiveDataRelease.State.EMPTY,
        )
