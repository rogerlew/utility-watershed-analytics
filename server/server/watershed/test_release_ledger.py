import hashlib
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from server.watershed.models import (
    ActiveDataRelease,
    DataArtifactLineage,
    DataRelease,
    DataReleaseAttempt,
    DataRunState,
    RunCapability,
    WatershedCollection,
    WatershedIdentity,
)
from server.watershed.release_ledger import (
    ActivationError,
    InvalidTransitionError,
    LeaseConflictError,
    activate_release,
    begin_release_attempt,
    transition_attempt,
)


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def create_identity(suffix="ledger"):
    collection = WatershedCollection.objects.create(key=f"collection-{suffix}")
    identity = WatershedIdentity.objects.create(
        watershed_key=f"watershed-{suffix}",
        collection=collection,
    )
    return collection, identity


def create_release(number, collection, identity, previous=None, capability=True):
    release = DataRelease.objects.create(
        release_id=f"2026-07-17.{number}",
        manifest_sha256=digest(f"manifest-{number}"),
        release_fingerprint=digest(f"release-{number}"),
        domain_fingerprint=digest(f"domain-{number}"),
        supported_migration="watershed.0009_release_ledger_capabilities",
        materializer_image_digest=f"sha256:{digest(f'image-{number}')}",
        materializer_git_commit=digest(f"commit-{number}")[:40],
        previous_release=previous,
        expected_watersheds=1,
        expected_subcatchments=2,
        expected_channels=3,
        actual_watersheds=1,
        actual_subcatchments=2,
        actual_channels=3,
        validation_summary={"status": "passed"},
        created_at=timezone.now(),
    )
    capability_fingerprint = digest(f"capability-{number}") if capability else None
    run_state = DataRunState.objects.create(
        release=release,
        collection=collection,
        watershed_identity=identity,
        runid=f"source/run-{number}",
        run_fingerprint=digest(f"run-{number}"),
        metadata_fingerprint=digest(f"metadata-{number}"),
        geometry_fingerprint=digest(f"geometry-{number}"),
        subcatchment_fingerprint=digest(f"subcatchment-{number}"),
        channel_fingerprint=digest(f"channel-{number}"),
        hillslope_fingerprint=digest(f"hillslope-{number}"),
        soil_fingerprint=digest(f"soil-{number}"),
        landuse_fingerprint=digest(f"landuse-{number}"),
        transformation_lineage_fingerprint=digest(f"transform-{number}"),
        capability_fingerprint=capability_fingerprint,
        actual_subcatchments=2,
        actual_channels=3,
    )
    DataArtifactLineage.objects.create(
        run_state=run_state,
        role="boundary",
        uri=f"https://artifacts.example.test/release-{number}/boundary.geojson",
        sha256=digest(f"boundary-artifact-{number}"),
        byte_size=1024,
        media_type="application/geo+json",
    )
    capability_row = None
    if capability:
        capability_row = RunCapability.objects.create(
            run_state=run_state,
            watershed_identity=identity,
            mode=RunCapability.Mode.BOTH,
            durable_base_uri=(
                f"https://artifacts.example.test/release-{number}/rhessys/"
            ),
            index_uri=(
                f"https://artifacts.example.test/release-{number}/rhessys/index.json"
            ),
            index_sha256=digest(f"index-{number}"),
            capability_fingerprint=capability_fingerprint,
            runtime_configuration={"scenarios": ["burned"]},
        )
    return release, run_state, capability_row


def begin_attempt(release, actor_kind=DataReleaseAttempt.ActorKind.OPERATOR):
    return begin_release_attempt(
        release=release,
        actor_kind=actor_kind,
        actor_identifier=("roger" if actor_kind == "operator" else "github:12345"),
        target_environment="test",
        application_git_commit=digest("application")[:40],
        reviewed_plan_sha256=digest(f"plan-{release.release_id}"),
        lease_owner=f"forest1:{release.release_id}",
    )


def prepare_attempt(release):
    attempt = begin_attempt(release)
    attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
    return transition_attempt(
        attempt,
        DataReleaseAttempt.Status.APPLYING,
        actual_plan_sha256=attempt.reviewed_plan_sha256,
    )


class ReleaseLedgerConstraintTests(TestCase):
    def test_singleton_and_version_constraints_are_database_enforced(self):
        active = ActiveDataRelease.objects.get(singleton_id=1)
        self.assertEqual(active.state, ActiveDataRelease.State.EMPTY)
        self.assertIsNone(active.release_id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ActiveDataRelease.objects.bulk_create(
                [ActiveDataRelease(singleton_id=2, state="EMPTY")]
            )

        invalid = DataRelease(
            release_id="2026-07-17.90",
            manifest_sha256=digest("invalid-manifest"),
            release_fingerprint=digest("invalid-release"),
            domain_fingerprint=digest("invalid-domain"),
            schema_version=2,
            supported_migration="watershed.0009_release_ledger_capabilities",
            materializer_image_digest=f"sha256:{digest('invalid-image')}",
            materializer_git_commit=digest("invalid-commit")[:40],
            expected_watersheds=0,
            expected_subcatchments=0,
            expected_channels=0,
            actual_watersheds=0,
            actual_subcatchments=0,
            actual_channels=0,
            created_at=timezone.now(),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            DataRelease.objects.bulk_create([invalid])

    def test_release_and_artifact_payloads_are_immutable(self):
        collection, identity = create_identity("immutable")
        release, run_state, _ = create_release(1, collection, identity)
        release.manifest_sha256 = digest("changed")
        with self.assertRaisesRegex(ValidationError, "Immutable release"):
            release.save()
        release.refresh_from_db()
        release.status = DataRelease.Status.ACTIVE
        with self.assertRaisesRegex(ValidationError, "activation helper"):
            release.save()
        artifact = run_state.artifacts.get()
        artifact.uri = "https://artifacts.example.test/changed.json"
        with self.assertRaisesRegex(ValidationError, "immutable"):
            artifact.save()

    def test_release_run_artifact_and_capability_uniqueness(self):
        collection, identity = create_identity("unique")
        release, run_state, capability = create_release(1, collection, identity)
        duplicate_run = DataRunState(
            release=release,
            collection=collection,
            watershed_identity=identity,
            runid="another-run",
            run_fingerprint=digest("dup-run"),
            metadata_fingerprint=digest("dup-meta"),
            geometry_fingerprint=digest("dup-geometry"),
            subcatchment_fingerprint=digest("dup-subcatchments"),
            channel_fingerprint=digest("dup-channels"),
            hillslope_fingerprint=digest("dup-hillslopes"),
            soil_fingerprint=digest("dup-soils"),
            landuse_fingerprint=digest("dup-landuse"),
            actual_subcatchments=0,
            actual_channels=0,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            DataRunState.objects.bulk_create([duplicate_run])

        duplicate_capability = RunCapability(
            run_state=run_state,
            watershed_identity=identity,
            mode=RunCapability.Mode.DYNAMIC,
            durable_base_uri="https://artifacts.example.test/duplicate/",
            index_uri="https://artifacts.example.test/duplicate/index.json",
            index_sha256=digest("duplicate-index"),
            capability_fingerprint=capability.capability_fingerprint,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RunCapability.objects.bulk_create([duplicate_capability])

    def test_capability_rejects_secret_configuration_and_identity_mismatch(self):
        collection, identity = create_identity("configuration")
        release, run_state, capability = create_release(
            1, collection, identity, capability=False
        )
        run_state.capability_fingerprint = digest("configuration-capability")
        run_state.save()
        with self.assertRaisesRegex(ValidationError, "Secret-bearing"):
            RunCapability.objects.create(
                run_state=run_state,
                watershed_identity=identity,
                mode=RunCapability.Mode.DYNAMIC,
                durable_base_uri="https://artifacts.example.test/configuration/",
                index_uri=(
                    "https://artifacts.example.test/configuration/index.json"
                ),
                index_sha256=digest("configuration-index"),
                capability_fingerprint=run_state.capability_fingerprint,
                runtime_configuration={"api_key": "not-allowed"},
            )
        self.assertIsNone(capability)
        self.assertEqual(release.run_states.count(), 1)


class ReleaseAttemptTests(TestCase):
    def test_operator_workflow_attribution_and_expired_lease_hold(self):
        collection, identity = create_identity("lease")
        first, _, _ = create_release(1, collection, identity)
        second, _, _ = create_release(2, collection, identity, previous=first)
        attempt = begin_attempt(first)
        self.assertEqual(attempt.actor_kind, "operator")
        with self.assertRaisesRegex(LeaseConflictError, "already active"):
            begin_attempt(second, DataReleaseAttempt.ActorKind.WORKFLOW)

        now = timezone.now()
        DataReleaseAttempt.objects.filter(pk=attempt.pk).update(
            lease_heartbeat_at=now - timedelta(hours=2),
            lease_expires_at=now - timedelta(hours=1),
        )
        attempt.refresh_from_db()
        self.assertTrue(attempt.lease_expired)
        with self.assertRaisesRegex(LeaseConflictError, "recovery required"):
            begin_attempt(second, DataReleaseAttempt.ActorKind.WORKFLOW)

        attempt = transition_attempt(
            attempt,
            DataReleaseAttempt.Status.FAILED,
            failure_phase="fetch",
            failure_summary=(
                "token=example-value\n"
                "https://example-user:example-password@example.test/path"
            ),
        )
        self.assertNotIn("example-value", attempt.failure_summary)
        self.assertNotIn("example-password", attempt.failure_summary)
        self.assertNotIn("\n", attempt.failure_summary)
        self.assertIn("[REDACTED]", attempt.failure_summary)

        workflow_attempt = begin_attempt(
            second, DataReleaseAttempt.ActorKind.WORKFLOW
        )
        self.assertEqual(workflow_attempt.actor_identifier, "github:12345")

    def test_state_machine_rejects_skips_and_records_terminal_states(self):
        collection, identity = create_identity("transition")
        release, _, _ = create_release(1, collection, identity)
        attempt = begin_attempt(release)
        with self.assertRaises(InvalidTransitionError):
            transition_attempt(attempt, DataReleaseAttempt.Status.SUCCEEDED)
        attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
        with self.assertRaises(ValidationError):
            transition_attempt(attempt, DataReleaseAttempt.Status.APPLYING)
        attempt = transition_attempt(
            attempt,
            DataReleaseAttempt.Status.FAILED,
            failure_phase="validation",
            failure_summary="count mismatch",
        )
        self.assertFalse(attempt.lease_active)
        self.assertIsNotNone(attempt.completed_at)
        attempt = transition_attempt(attempt, DataReleaseAttempt.Status.ROLLED_BACK)
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.ROLLED_BACK)


class ReleaseActivationTests(TestCase):
    def test_first_activation_exposes_only_target_capability(self):
        collection, identity = create_identity("first")
        release, _, capability = create_release(1, collection, identity)
        self.assertFalse(RunCapability.objects.visible().exists())
        attempt = prepare_attempt(release)
        active = activate_release(attempt)
        release.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(active.release_id, release.release_id)
        self.assertEqual(release.status, DataRelease.Status.ACTIVE)
        self.assertIsNotNone(release.first_activated_at)
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.SUCCEEDED)
        self.assertEqual(list(RunCapability.objects.visible()), [capability])

    def test_successor_activation_retains_history_and_switches_visibility(self):
        collection, identity = create_identity("successor")
        first, _, first_capability = create_release(1, collection, identity)
        activate_release(prepare_attempt(first))
        second, _, second_capability = create_release(
            2, collection, identity, previous=first
        )
        self.assertEqual(list(RunCapability.objects.visible()), [first_capability])
        activate_release(prepare_attempt(second))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, DataRelease.Status.SUPERSEDED)
        self.assertEqual(second.status, DataRelease.Status.ACTIVE)
        self.assertEqual(DataRelease.objects.count(), 2)
        self.assertEqual(DataRunState.objects.count(), 2)
        self.assertEqual(list(RunCapability.objects.visible()), [second_capability])

    def test_superseded_release_can_be_reactivated_for_rollback(self):
        collection, identity = create_identity("rollback")
        first, _, first_capability = create_release(1, collection, identity)
        activate_release(prepare_attempt(first))
        second, _, _ = create_release(2, collection, identity, previous=first)
        activate_release(prepare_attempt(second))
        activate_release(prepare_attempt(first))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, DataRelease.Status.ACTIVE)
        self.assertEqual(second.status, DataRelease.Status.SUPERSEDED)
        self.assertEqual(list(RunCapability.objects.visible()), [first_capability])

    def test_plan_or_capability_mismatch_leaves_active_pointer_unchanged(self):
        collection, identity = create_identity("mismatch")
        release, run_state, capability = create_release(1, collection, identity)
        attempt = begin_attempt(release)
        attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
        attempt = transition_attempt(
            attempt,
            DataReleaseAttempt.Status.APPLYING,
            actual_plan_sha256=digest("different-plan"),
        )
        with self.assertRaisesRegex(ActivationError, "plans differ"):
            activate_release(attempt)
        active = ActiveDataRelease.objects.get(singleton_id=1)
        self.assertEqual(active.state, ActiveDataRelease.State.EMPTY)
        self.assertFalse(RunCapability.objects.visible().exists())

        DataReleaseAttempt.objects.filter(pk=attempt.pk).update(
            actual_plan_sha256=attempt.reviewed_plan_sha256
        )
        RunCapability.objects.filter(pk=capability.pk).update(
            capability_fingerprint=digest("mismatched-capability")
        )
        with self.assertRaisesRegex(ActivationError, "fingerprint mismatch"):
            activate_release(attempt)
        self.assertEqual(run_state.release.status, DataRelease.Status.VALIDATED)
