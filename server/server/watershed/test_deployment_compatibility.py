import hashlib
import json
from io import StringIO

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from server.watershed.deployment_compatibility import (
    DeploymentCompatibilityError,
    verify_application_compatibility,
    verify_release_compatibility,
)
from server.watershed.fingerprint_contract import canonical_sha256
from server.watershed.materializer import CORE_ARTIFACT_MEDIA_TYPES
from server.watershed.models import (
    ActiveDataRelease,
    DataArtifactLineage,
    DataRelease,
    DataReleaseAttempt,
    DataRunState,
    WatershedCollection,
    WatershedIdentity,
    WatershedRunAlias,
)
from server.watershed.release_ledger import begin_release_attempt, transition_attempt
from server.watershed.staging import SpaceBudget, mark_staging_ready, open_staging
from server.watershed.staging_models import DataReleaseStagingState, StagedWatershed


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class DeploymentCompatibilityTests(TestCase):
    migration = "watershed.0011_capability_runtime_types"
    image_digest = f"sha256:{digest('db25-image')}"
    materializer_git = digest("db25-materializer")[:40]
    application_git = digest("db25-application")[:40]

    def release(self, release_id="2026-07-18.250", *, watershed_rows=0):
        return DataRelease.objects.create(
            release_id=release_id,
            manifest_sha256=digest(f"manifest-{release_id}"),
            release_fingerprint=digest(f"release-{release_id}"),
            domain_fingerprint=digest(f"domain-{release_id}"),
            supported_migration=self.migration,
            materializer_image_digest=self.image_digest,
            materializer_git_commit=self.materializer_git,
            expected_watersheds=watershed_rows,
            expected_subcatchments=0,
            expected_channels=0,
            actual_watersheds=watershed_rows,
            actual_subcatchments=0,
            actual_channels=0,
            validation_summary={"synthetic": True},
            created_at=timezone.now(),
        )

    def plan(self, release):
        return {
            "schema_version": 1,
            "plan_kind": "empty-build",
            "plan_id": "db25-synthetic-empty",
            "fingerprint_version": 1,
            "data_contract": 1,
            "identity_contract": 1,
            "supported_migration": self.migration,
            "materializer": {
                "image_digest": self.image_digest,
                "git_commit": self.materializer_git,
            },
            "base": {"kind": "EMPTY"},
            "target": {
                "kind": "RELEASE",
                "release_id": release.release_id,
                "manifest_sha256": release.manifest_sha256,
                "release_fingerprint": release.release_fingerprint,
                "domain_fingerprint": release.domain_fingerprint,
            },
            "actions": [],
            "expected_row_delta": {
                "watersheds": release.actual_watersheds,
                "subcatchments": 0,
                "channels": 0,
            },
        }

    def ready_attempt(self, release, plan):
        attempt = begin_release_attempt(
            release=release,
            actor_kind=DataReleaseAttempt.ActorKind.WORKFLOW,
            actor_identifier="db25-test",
            target_environment="test",
            application_git_commit=self.application_git,
            reviewed_plan_sha256=canonical_sha256(plan),
            lease_owner="db25-test",
        )
        attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
        open_staging(
            attempt,
            budget=SpaceBudget(0, 0, 0, 0, 0, 0),
            observed_available_bytes=0,
        )
        return attempt

    def verify(self, release, attempt, plan, **overrides):
        options = {
            "expected_base_manifest": "EMPTY",
            "materializer_image_digest": self.image_digest,
            "materializer_git_commit": self.materializer_git,
            "application_git_commit": self.application_git,
        }
        options.update(overrides)
        return verify_release_compatibility(release, attempt, plan, **options)

    def test_application_and_empty_release_compatibility(self):
        application = verify_application_compatibility()
        self.assertEqual(application.active_state, ActiveDataRelease.State.EMPTY)
        release = self.release()
        plan = self.plan(release)
        attempt = self.ready_attempt(release, plan)
        mark_staging_ready(attempt)

        result = self.verify(release, attempt, plan)

        self.assertEqual(result.active_base, "EMPTY")
        self.assertEqual(result.artifact_rows, 0)
        self.assertEqual(result.capability_rows, 0)

    def test_wrong_image_git_plan_base_and_application_commit_fail(self):
        release = self.release()
        plan = self.plan(release)
        attempt = self.ready_attempt(release, plan)
        mark_staging_ready(attempt)
        cases = (
            {"materializer_image_digest": f"sha256:{digest('wrong')}"},
            {"materializer_git_commit": digest("wrong-git")[:40]},
            {"application_git_commit": digest("wrong-app")[:40]},
            {"expected_base_manifest": digest("stale-base")},
        )
        for options in cases:
            with self.subTest(options=options):
                with self.assertRaises(DeploymentCompatibilityError):
                    self.verify(release, attempt, plan, **options)
        changed_plan = json.loads(json.dumps(plan))
        changed_plan["target"]["domain_fingerprint"] = digest("changed")
        with self.assertRaises(DeploymentCompatibilityError):
            self.verify(release, attempt, changed_plan)

    def test_incompatible_active_migration_fails_application_check(self):
        release = self.release()
        DataRelease.objects.filter(pk=release.pk).update(
            supported_migration="watershed.0001_initial",
            status=DataRelease.Status.ACTIVE,
        )
        release.refresh_from_db()
        active = ActiveDataRelease.objects.get(singleton_id=1)
        active.state = ActiveDataRelease.State.ACTIVE
        active.release = release
        active.manifest_sha256 = release.manifest_sha256
        active.data_contract = release.data_contract
        active.activated_at = timezone.now()
        active._allow_activation_change = True
        active.save()

        with self.assertRaises(DeploymentCompatibilityError):
            verify_application_compatibility()

    def test_incomplete_artifacts_and_capabilities_fail_before_activation(self):
        release = self.release(watershed_rows=1)
        collection = WatershedCollection.objects.create(key="db25")
        identity = WatershedIdentity.objects.create(
            watershed_key="db25-watershed",
            collection=collection,
        )
        WatershedRunAlias.objects.create(
            runid="db25-run",
            watershed_identity=identity,
            is_current=True,
        )
        state = DataRunState.objects.create(
            release=release,
            collection=collection,
            watershed_identity=identity,
            runid="db25-run",
            run_fingerprint=digest("run"),
            metadata_fingerprint=digest("metadata"),
            geometry_fingerprint=digest("geometry"),
            subcatchment_fingerprint=digest("subcatchments"),
            channel_fingerprint=digest("channels"),
            hillslope_fingerprint=digest("hillslopes"),
            soil_fingerprint=digest("soils"),
            landuse_fingerprint=digest("landuse"),
            actual_subcatchments=0,
            actual_channels=0,
        )
        plan = self.plan(release)
        plan["actions"] = [
            {
                "watershed_key": identity.watershed_key,
                "operation": "add",
                "before": None,
                "after": {
                    "runid": state.runid,
                    "run_fingerprint": state.run_fingerprint,
                    "capability_fingerprint": None,
                },
                "change_channels": ["identity", "metadata", "geometry", "children"],
                "row_delta": {"watersheds": 1, "subcatchments": 0, "channels": 0},
            }
        ]
        attempt = self.ready_attempt(release, plan)
        geometry = MultiPolygon(
            Polygon(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)), srid=4326),
            srid=4326,
        )
        StagedWatershed.objects.create(
            attempt=attempt,
            run_state=state,
            watershed_identity=identity,
            source_fingerprint=state.run_fingerprint,
            validation_status=StagedWatershed.ValidationStatus.VALIDATED,
            runid=state.runid,
            geom=geometry,
        )
        DataReleaseStagingState.objects.filter(attempt=attempt).update(watershed_rows=1)
        mark_staging_ready(attempt)
        with self.assertRaisesMessage(
            DeploymentCompatibilityError,
            "artifact roles",
        ):
            self.verify(release, attempt, plan)

        for role, media_type in CORE_ARTIFACT_MEDIA_TYPES.items():
            DataArtifactLineage.objects.create(
                run_state=state,
                role=role,
                uri=f"https://artifacts.example.test/{role}",
                sha256=digest(role),
                byte_size=1,
                media_type=media_type,
            )
        DataRunState.objects.filter(pk=state.pk).update(
            capability_fingerprint=digest("missing-capability")
        )
        with self.assertRaisesMessage(
            DeploymentCompatibilityError,
            "Staging counts",
        ):
            self.verify(release, attempt, plan)

    def test_management_commands_emit_sanitized_json(self):
        stdout = StringIO()
        call_command("check_application_compatibility", stdout=stdout)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "compatible")

        release = self.release()
        plan = self.plan(release)
        attempt = self.ready_attempt(release, plan)
        mark_staging_ready(attempt)
        with self.assertRaises(CommandError):
            call_command(
                "check_release_compatibility",
                release_id=release.release_id,
                attempt_id=str(attempt.pk),
                plan_file="/missing/db25-plan.json",
                expected_base_manifest="EMPTY",
                materializer_image_digest=self.image_digest,
                materializer_git_commit=self.materializer_git,
                application_git_commit=self.application_git,
            )
