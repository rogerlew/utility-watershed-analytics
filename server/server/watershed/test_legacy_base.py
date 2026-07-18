import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.test import TestCase

from server.watershed.legacy_base import (
    CapabilityBootstrap,
    LegacyBaseError,
    ReviewedIdentity,
    adopt_legacy_base,
    assign_reviewed_identities,
    export_legacy_base,
    install_baseline_ledger,
    load_legacy_baseline,
    materialization_members,
    rollback_legacy_adoption,
)
from server.watershed.domain_mutations import SUBCATCHMENT_FIELDS, WATERSHED_FIELDS
from server.watershed.models import (
    ActiveDataRelease,
    Channel,
    DataRelease,
    DataReleaseAttempt,
    RunCapability,
    Subcatchment,
    Watershed,
    WatershedCollection,
    WatershedIdentity,
    WatershedRunAlias,
)
from server.watershed.release_ledger import begin_release_attempt, transition_attempt
from server.watershed.release_validation import (
    compute_serving_fingerprints,
    validated_empty_build,
)
from server.watershed.staging import SpaceBudget


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def geometry(offset, size=1):
    polygon = Polygon(
        (
            (offset, 0),
            (offset + size, 0),
            (offset + size, size),
            (offset, size),
            (offset, 0),
        ),
        srid=4326,
    )
    return MultiPolygon(polygon, srid=4326)


class LegacyBaseToolingTests(TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for index, runid in enumerate(("legacy-one", "legacy-two"), start=1):
            watershed = Watershed.objects.create(
                runid=runid,
                srcname=f"Legacy {index}",
                state="WA",
                geom=geometry(index * 3),
                simplified_geom=geometry(index * 3 + 0.1, 0.8),
            )
            for topazid in (1, 2):
                Subcatchment.objects.create(
                    watershed=watershed,
                    topazid=topazid,
                    weppid=100 + topazid,
                    geom=geometry(index * 3 + topazid / 10, 0.3),
                    slope_scalar=topazid / 10,
                    mukey=str(100 + topazid),
                    landuse_key=topazid + 6,
                )
            Channel.objects.create(
                watershed=watershed,
                topazid=1,
                weppid=201,
                order=1,
                geom=geometry(index * 3 + 0.4, 0.2),
            )
        self.assignments = (
            ReviewedIdentity("legacy-one", "legacy", "legacy-watershed-one"),
            ReviewedIdentity(
                "legacy-two",
                "legacy",
                "legacy-watershed-two",
                aliases=("former-legacy-two",),
            ),
        )
        self.bootstrap = CapabilityBootstrap(
            runid="legacy-one",
            capability_type=RunCapability.CapabilityType.SBS,
            mode=RunCapability.Mode.PRECOMPUTED,
            durable_base_uri="https://artifacts.example.test/legacy/objects/sha256/",
            index_role="sbs-index",
            index_content=b'{"kind":"legacy-sbs","schema_version":1}\n',
            runtime_configuration={
                "schema_version": 1,
                "enabled": True,
                "access_policy": "public",
                "index_uri": "$INDEX_URI",
                "index_sha256": "$INDEX_SHA256",
                "geometry_revision": digest("legacy-geometry"),
                "artifact": {
                    "uri": "$ARTIFACT_URI:sbs-raster",
                    "sha256": "$ARTIFACT_SHA256:sbs-raster",
                    "bytes": "$ARTIFACT_BYTES:sbs-raster",
                    "media_type": "image/tiff",
                    "verified": True,
                },
            },
            runtime_artifacts={
                "sbs-raster": (b"synthetic immutable SBS raster", "image/tiff")
            },
        )

    def export(self, **overrides):
        assign_reviewed_identities(self.assignments)
        options = {
            "release_id": "2026-07-18.211",
            "artifact_base_uri": "https://artifacts.example.test/legacy",
            "supported_migration": "watershed.0011_capability_runtime_types",
            "materializer_git_commit": "1" * 40,
            "materializer_image_digest": f"sha256:{'2' * 64}",
            "capabilities": (self.bootstrap,),
        }
        options.update(overrides)
        baseline = export_legacy_base(self.root, **options)
        return load_legacy_baseline(self.root, baseline.manifest_sha256)

    def domain_snapshot(self):
        return {
            "watersheds": list(
                Watershed.objects.order_by("runid").values_list(
                    "runid", "logical_watershed_id", "srcname", "state"
                )
            ),
            "subcatchments": list(
                Subcatchment.objects.order_by("watershed_id", "topazid").values_list(
                    "id",
                    "watershed_id",
                    "logical_watershed_id",
                    "topazid",
                    "weppid",
                    "slope_scalar",
                    "mukey",
                    "landuse_key",
                )
            ),
            "channels": list(
                Channel.objects.order_by("watershed_id").values_list(
                    "id",
                    "watershed_id",
                    "logical_watershed_id",
                    "topazid",
                    "weppid",
                    "order",
                )
            ),
            "content_types": ContentType.objects.count(),
        }

    def rebuild_snapshot(self):
        return {
            "watersheds": [
                (
                    row.runid,
                    row.geom.hexewkb,
                    row.simplified_geom.hexewkb if row.simplified_geom else None,
                    {field: getattr(row, field) for field in WATERSHED_FIELDS},
                )
                for row in Watershed.objects.order_by("runid")
            ],
            "subcatchments": [
                (
                    row.watershed_id,
                    row.topazid,
                    row.weppid,
                    row.geom.hexewkb,
                    {field: getattr(row, field) for field in SUBCATCHMENT_FIELDS},
                )
                for row in Subcatchment.objects.order_by("watershed_id", "topazid")
            ],
            "channels": list(
                Channel.objects.order_by(
                    "watershed_id", "topazid", "weppid", "order"
                ).values_list("watershed_id", "topazid", "weppid", "order", "geom")
            ),
        }

    def test_adoption_and_rollback_preserve_preexisting_rows(self):
        baseline = self.export()
        before = self.domain_snapshot()
        release = adopt_legacy_base(
            baseline,
            actor_identifier="synthetic-operator",
            application_git_commit="3" * 40,
            reviewed_plan_sha256="4" * 64,
        )
        active = ActiveDataRelease.objects.get(singleton_id=1)
        self.assertEqual(active.release, release)
        self.assertEqual(active.state, ActiveDataRelease.State.ACTIVE)
        self.assertEqual(RunCapability.objects.count(), 1)
        self.assertEqual(self.domain_snapshot(), before)
        with self.assertRaisesRegex(LegacyBaseError, "requires EMPTY"):
            adopt_legacy_base(
                baseline,
                actor_identifier="synthetic-operator",
                application_git_commit="3" * 40,
                reviewed_plan_sha256="4" * 64,
            )
        self.assertEqual(self.domain_snapshot(), before)

        rollback_legacy_adoption(baseline)
        active.refresh_from_db()
        self.assertEqual(active.state, ActiveDataRelease.State.EMPTY)
        self.assertIsNone(active.release_id)
        self.assertEqual(RunCapability.objects.count(), 0)
        self.assertEqual(self.domain_snapshot(), before)
        self.assertTrue(DataRelease.objects.filter(pk=release.pk).exists())
        self.assertEqual(
            release.attempts.get().status,
            DataReleaseAttempt.Status.ROLLED_BACK,
        )

    def test_fingerprint_mismatch_rolls_back_all_adoption_state(self):
        baseline = self.export()
        child = Subcatchment.objects.order_by("id").first()
        child.slope_scalar = 9.9
        child.save(update_fields=("slope_scalar",))
        before = self.domain_snapshot()
        with self.assertRaisesRegex(LegacyBaseError, "fingerprints differ"):
            adopt_legacy_base(
                baseline,
                actor_identifier="synthetic-operator",
                application_git_commit="3" * 40,
                reviewed_plan_sha256="4" * 64,
            )
        self.assertEqual(self.domain_snapshot(), before)
        self.assertFalse(DataRelease.objects.exists())
        self.assertFalse(RunCapability.objects.exists())
        self.assertFalse(DataReleaseAttempt.objects.exists())
        self.assertEqual(
            ActiveDataRelease.objects.get(singleton_id=1).state,
            ActiveDataRelease.State.EMPTY,
        )

    def test_checksum_and_migration_mismatch_are_non_mutating(self):
        baseline = self.export()
        before = self.domain_snapshot()
        first_reference = baseline.document["members"][0]["artifacts"]["metadata"]
        baseline.artifact_path(first_reference["sha256"]).write_bytes(b"changed")
        with self.assertRaisesRegex(LegacyBaseError, "artifact bytes differ"):
            adopt_legacy_base(
                baseline,
                actor_identifier="synthetic-operator",
                application_git_commit="3" * 40,
                reviewed_plan_sha256="4" * 64,
            )
        self.assertFalse(DataRelease.objects.exists())
        self.assertEqual(self.domain_snapshot(), before)

        other_root = self.root / "wrong-migration"
        baseline = export_legacy_base(
            other_root,
            release_id="2026-07-18.212",
            artifact_base_uri="https://artifacts.example.test/legacy",
            supported_migration="watershed.0010_attempt_scoped_staging",
            materializer_git_commit="1" * 40,
            materializer_image_digest=f"sha256:{'2' * 64}",
        )
        with self.assertRaisesRegex(LegacyBaseError, "current leaf"):
            adopt_legacy_base(
                baseline,
                actor_identifier="synthetic-operator",
                application_git_commit="3" * 40,
                reviewed_plan_sha256="4" * 64,
            )
        self.assertFalse(DataRelease.objects.exists())

        invalid_bootstrap = CapabilityBootstrap(
            **{
                **self.bootstrap.__dict__,
                "runtime_configuration": {
                    **self.bootstrap.runtime_configuration,
                    "access_policy": "unsupported",
                },
            }
        )
        baseline = export_legacy_base(
            self.root / "invalid-capability",
            release_id="2026-07-18.213",
            artifact_base_uri="https://artifacts.example.test/legacy",
            supported_migration="watershed.0011_capability_runtime_types",
            materializer_git_commit="1" * 40,
            materializer_image_digest=f"sha256:{'2' * 64}",
            capabilities=(invalid_bootstrap,),
        )
        with self.assertRaisesRegex(LegacyBaseError, "bootstrap is invalid"):
            adopt_legacy_base(
                baseline,
                actor_identifier="synthetic-operator",
                application_git_commit="3" * 40,
                reviewed_plan_sha256="4" * 64,
            )
        self.assertFalse(DataRelease.objects.exists())
        self.assertFalse(RunCapability.objects.exists())

    def test_exported_artifacts_rebuild_exact_fingerprints_offline(self):
        baseline = self.export()
        expected_domain = baseline.document["domain_fingerprint"]
        expected_capabilities = baseline.document["capability_fingerprint"]
        expected_rows = self.rebuild_snapshot()

        Channel.objects.all().delete()
        Subcatchment.objects.all().delete()
        Watershed.objects.all().delete()
        WatershedRunAlias.objects.all().delete()
        WatershedIdentity.objects.all().delete()
        WatershedCollection.objects.all().delete()

        release = install_baseline_ledger(baseline)
        members = materialization_members(baseline, release)
        attempt = begin_release_attempt(
            release=release,
            actor_kind=DataReleaseAttempt.ActorKind.OPERATOR,
            actor_identifier="offline-rebuild",
            target_environment="test",
            application_git_commit="3" * 40,
            reviewed_plan_sha256="4" * 64,
            lease_owner="offline-rebuild",
        )
        attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
        artifact_bytes = sum(
            path.stat().st_size
            for member in members
            for path in member.artifact_paths.values()
        )
        budget = SpaceBudget(artifact_bytes, 1024, 1024, 1024, 1024, 1024)
        result = validated_empty_build(
            attempt,
            members,
            budget=budget,
            observed_available_bytes=budget.required_bytes,
            actual_plan_sha256="4" * 64,
            validator_git_commit="5" * 40,
            validator_image_digest=f"sha256:{'6' * 64}",
            reviewed_bounds={
                member["runid"]: tuple(float(value) for value in member["bounds"])
                for member in baseline.document["members"]
            },
            batch_size=1,
        )
        self.assertEqual(self.rebuild_snapshot(), expected_rows)
        self.assertEqual(result.fingerprints.domain, expected_domain)
        self.assertEqual(result.fingerprints.capabilities, expected_capabilities)
        self.assertEqual(compute_serving_fingerprints(release), result.fingerprints)

    def test_reviewed_identity_membership_is_exact(self):
        before = self.domain_snapshot()
        with self.assertRaisesRegex(LegacyBaseError, "membership differs"):
            assign_reviewed_identities(self.assignments[:1])
        self.assertEqual(self.domain_snapshot(), before)
        self.assertFalse(WatershedIdentity.objects.exists())
