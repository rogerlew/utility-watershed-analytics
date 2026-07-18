import hashlib
from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.test import TestCase
from django.utils import timezone

from server.watershed.models import (
    ActiveDataRelease,
    Channel,
    DataRelease,
    DataReleaseAttempt,
    DataRunState,
    RunCapability,
    Subcatchment,
    Watershed,
    WatershedCollection,
    WatershedIdentity,
)
from server.watershed.release_ledger import (
    LeaseConflictError,
    activate_release,
    begin_release_attempt,
    transition_attempt,
)
from server.watershed.staging import (
    SpaceBudget,
    available_bytes,
    cleanup_staging,
    load_staging_rows,
    open_staging,
    recover_expired_attempts,
    retry_pending_cleanup,
)
from server.watershed.staging_models import (
    DataReleaseStagingState,
    StagedChannel,
    StagedRunCapability,
    StagedSubcatchment,
    StagedWatershed,
)


GEOMETRY = "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def budget():
    return SpaceBudget(
        artifact_bytes=10,
        staging_bytes=20,
        index_bytes=30,
        backup_bytes=40,
        wal_bytes=50,
        margin_bytes=60,
    )


def create_release(number, *, identity=None, collection=None, previous=None, capability=False):
    if collection is None:
        collection = WatershedCollection.objects.create(key=f"stage-collection-{number}")
    if identity is None:
        identity = WatershedIdentity.objects.create(
            watershed_key=f"stage-watershed-{number}",
            collection=collection,
        )
    release = DataRelease.objects.create(
        release_id=f"2026-07-18.{number}",
        manifest_sha256=digest(f"manifest-{number}"),
        release_fingerprint=digest(f"release-{number}"),
        domain_fingerprint=digest(f"domain-{number}"),
        supported_migration="watershed.0010_attempt_scoped_staging",
        materializer_image_digest=f"sha256:{digest(f'image-{number}')}",
        materializer_git_commit=digest(f"commit-{number}")[:40],
        previous_release=previous,
        expected_watersheds=1,
        expected_subcatchments=2,
        expected_channels=1,
        actual_watersheds=1,
        actual_subcatchments=2,
        actual_channels=1,
        validation_summary={"status": "passed"},
        created_at=timezone.now(),
    )
    capability_fingerprint = digest(f"capability-{number}") if capability else None
    run_state = DataRunState.objects.create(
        release=release,
        collection=collection,
        watershed_identity=identity,
        runid=f"stage/run-{number}",
        run_fingerprint=digest(f"run-{number}"),
        metadata_fingerprint=digest(f"metadata-{number}"),
        geometry_fingerprint=digest(f"geometry-{number}"),
        subcatchment_fingerprint=digest(f"subcatchments-{number}"),
        channel_fingerprint=digest(f"channels-{number}"),
        hillslope_fingerprint=digest(f"hillslopes-{number}"),
        soil_fingerprint=digest(f"soils-{number}"),
        landuse_fingerprint=digest(f"landuse-{number}"),
        capability_fingerprint=capability_fingerprint,
        actual_subcatchments=2,
        actual_channels=1,
    )
    capability_row = None
    if capability:
        capability_row = RunCapability.objects.create(
            run_state=run_state,
            watershed_identity=identity,
            mode=RunCapability.Mode.BOTH,
            durable_base_uri=f"https://artifacts.example.test/{number}/rhessys/",
            index_uri=f"https://artifacts.example.test/{number}/index.json",
            index_sha256=digest(f"index-{number}"),
            capability_fingerprint=capability_fingerprint,
            runtime_configuration={"scenarios": ["burned"]},
        )
    return collection, identity, release, run_state, capability_row


def begin_attempt(release):
    return begin_release_attempt(
        release=release,
        actor_kind=DataReleaseAttempt.ActorKind.OPERATOR,
        actor_identifier="roger",
        target_environment="test",
        application_git_commit=digest("application")[:40],
        reviewed_plan_sha256=digest(f"plan-{release.release_id}"),
        lease_owner=f"forest1:{release.release_id}",
    )


def begin_staging(release):
    return transition_attempt(
        begin_attempt(release),
        DataReleaseAttempt.Status.STAGING,
    )


def open_loading(attempt, *, retention_until=None):
    return open_staging(
        attempt,
        budget=budget(),
        observed_available_bytes=budget().required_bytes,
        retention_until=retention_until,
    )


def watershed_values(run_state, identity):
    return {
        "run_state": run_state,
        "watershed_identity": identity,
        "source_fingerprint": run_state.run_fingerprint,
        "runid": run_state.runid,
        "geom": GEOSGeometry(GEOMETRY),
        "metadata": {"srcname": "Synthetic"},
    }


def subcatchment_values(run_state, identity, topazid):
    return {
        "run_state": run_state,
        "watershed_identity": identity,
        "source_fingerprint": run_state.subcatchment_fingerprint,
        "topazid": topazid,
        "weppid": topazid,
        "geom": GEOSGeometry(GEOMETRY),
        "attributes": {"slope_scalar": 0.1},
    }


def channel_values(run_state, identity, topazid):
    return {
        "run_state": run_state,
        "watershed_identity": identity,
        "source_fingerprint": run_state.channel_fingerprint,
        "topazid": topazid,
        "weppid": topazid,
        "order": 1,
        "geom": GEOSGeometry(GEOMETRY),
        "attributes": {},
    }


class StagingSchemaTests(TestCase):
    def test_tables_are_logged_and_constraints_and_indexes_exist(self):
        tables = (
            DataReleaseStagingState._meta.db_table,
            StagedWatershed._meta.db_table,
            StagedSubcatchment._meta.db_table,
            StagedChannel._meta.db_table,
            StagedRunCapability._meta.db_table,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT relname, relpersistence FROM pg_class WHERE relname = ANY(%s)",
                [list(tables)],
            )
            persistence = dict(cursor.fetchall())
            constraints = {}
            for table in tables:
                constraints.update(connection.introspection.get_constraints(cursor, table))
        self.assertEqual(persistence, {table: "p" for table in tables})
        for name in (
            "staging_state_space_outcome",
            "stage_ws_attempt_identity_uniq",
            "stage_sub_attempt_topaz_uniq",
            "stage_channel_attempt_key_uniq",
            "stage_cap_attempt_type_uniq",
            "stage_ws_attempt_status_idx",
            "stage_sub_attempt_ws_idx",
            "stage_channel_attempt_ws_idx",
            "stage_cap_attempt_ws_idx",
        ):
            self.assertIn(name, constraints)

    def test_duplicate_current_batch_and_secret_payload_fail_without_rows(self):
        _, identity, release, run_state, _ = create_release(1)
        attempt = begin_staging(release)
        open_loading(attempt)
        duplicates = [
            subcatchment_values(run_state, identity, 1),
            subcatchment_values(run_state, identity, 1),
        ]
        with self.assertRaises(IntegrityError):
            load_staging_rows(attempt, subcatchments=duplicates, batch_size=10)
        self.assertEqual(StagedSubcatchment.objects.count(), 0)
        state = DataReleaseStagingState.objects.get(attempt=attempt)
        self.assertEqual(state.subcatchment_rows, 0)

        invalid = watershed_values(run_state, identity)
        invalid["metadata"] = {"token": "not-allowed"}
        with self.assertRaisesRegex(ValidationError, "Secret-bearing"):
            load_staging_rows(attempt, watersheds=[invalid])
        self.assertEqual(StagedWatershed.objects.count(), 0)


class StagingCapacityAndLoadTests(TestCase):
    def test_capacity_accounts_for_every_component_and_exact_fit(self):
        _, _, release, _, _ = create_release(1)
        attempt = begin_staging(release)
        state = open_loading(attempt)
        self.assertEqual(state.required_bytes, 210)
        self.assertEqual(state.available_bytes, 210)
        self.assertEqual(state.status, DataReleaseStagingState.Status.LOADING)
        with TemporaryDirectory() as directory:
            self.assertGreater(available_bytes(directory), 0)

    def test_one_byte_short_fails_attempt_before_writing_rows(self):
        _, _, release, _, _ = create_release(1)
        attempt = begin_staging(release)
        state = open_staging(
            attempt,
            budget=budget(),
            observed_available_bytes=budget().required_bytes - 1,
        )
        attempt.refresh_from_db()
        self.assertEqual(
            state.status,
            DataReleaseStagingState.Status.SPACE_REJECTED,
        )
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.FAILED)
        self.assertFalse(attempt.lease_active)
        self.assertEqual(StagedWatershed.objects.count(), 0)

    def test_chunked_loader_stays_bounded_and_heartbeats(self):
        _, identity, release, run_state, _ = create_release(1)
        attempt = begin_staging(release)
        original_heartbeat = attempt.lease_heartbeat_at
        open_loading(attempt)

        def records():
            for topazid in range(1, 2502):
                yield subcatchment_values(run_state, identity, topazid)

        result = load_staging_rows(
            attempt,
            watersheds=[watershed_values(run_state, identity)],
            subcatchments=records(),
            channels=[channel_values(run_state, identity, 1)],
            batch_size=128,
        )
        attempt.refresh_from_db()
        state = DataReleaseStagingState.objects.get(attempt=attempt)
        self.assertEqual(result.subcatchment_rows, 2501)
        self.assertLessEqual(result.maximum_batch_rows, 128)
        self.assertEqual(StagedSubcatchment.objects.count(), 2501)
        self.assertEqual(state.subcatchment_rows, 2501)
        self.assertEqual(state.status, DataReleaseStagingState.Status.READY)
        self.assertGreater(attempt.lease_heartbeat_at, original_heartbeat)

    def test_crash_keeps_only_complete_committed_chunks(self):
        _, identity, release, run_state, _ = create_release(1)
        attempt = begin_staging(release)
        open_loading(attempt)

        def crashing_records():
            for topazid in range(1, 252):
                if topazid == 251:
                    raise RuntimeError("synthetic process crash")
                yield subcatchment_values(run_state, identity, topazid)

        with self.assertRaisesRegex(RuntimeError, "synthetic process crash"):
            load_staging_rows(
                attempt,
                subcatchments=crashing_records(),
                batch_size=100,
            )
        state = DataReleaseStagingState.objects.get(attempt=attempt)
        self.assertEqual(StagedSubcatchment.objects.count(), 200)
        self.assertEqual(state.subcatchment_rows, 200)
        self.assertEqual(state.status, DataReleaseStagingState.Status.LOADING)


class StagingRecoveryTests(TestCase):
    def expire(self, attempt, *, now):
        DataReleaseAttempt.objects.filter(pk=attempt.pk).update(
            lease_heartbeat_at=now - timedelta(hours=2),
            lease_expires_at=now - timedelta(hours=1),
        )

    def test_concurrent_attempt_is_rejected_by_db15_lease(self):
        _, _, first, _, _ = create_release(1)
        _, _, second, _, _ = create_release(2, previous=first)
        begin_attempt(first)
        with self.assertRaises(LeaseConflictError):
            begin_attempt(second)

    def test_every_expired_nonterminal_state_is_terminalized(self):
        now = timezone.now()
        for number, status in enumerate(
            (
                DataReleaseAttempt.Status.PLANNING,
                DataReleaseAttempt.Status.STAGING,
                DataReleaseAttempt.Status.APPLYING,
            ),
            start=1,
        ):
            with self.subTest(status=status):
                _, _, release, _, _ = create_release(number)
                attempt = begin_attempt(release)
                if status in (
                    DataReleaseAttempt.Status.STAGING,
                    DataReleaseAttempt.Status.APPLYING,
                ):
                    attempt = transition_attempt(
                        attempt,
                        DataReleaseAttempt.Status.STAGING,
                    )
                    open_loading(
                        attempt,
                        retention_until=now - timedelta(seconds=1),
                    )
                if status == DataReleaseAttempt.Status.APPLYING:
                    attempt = transition_attempt(
                        attempt,
                        DataReleaseAttempt.Status.APPLYING,
                        actual_plan_sha256=attempt.reviewed_plan_sha256,
                    )
                self.expire(attempt, now=now)
                result = recover_expired_attempts(now=now)
                attempt.refresh_from_db()
                self.assertEqual(attempt.status, DataReleaseAttempt.Status.FAILED)
                self.assertEqual(result[0][1], status)
                if hasattr(attempt, "staging_state"):
                    attempt.staging_state.refresh_from_db()
                    self.assertEqual(
                        attempt.staging_state.status,
                        DataReleaseStagingState.Status.CLEANED,
                    )

    def test_retention_cleanup_failure_and_retry_are_explicit(self):
        now = timezone.now()
        _, identity, release, run_state, _ = create_release(1)
        attempt = begin_staging(release)
        open_loading(attempt, retention_until=now + timedelta(hours=1))
        load_staging_rows(
            attempt,
            watersheds=[watershed_values(run_state, identity)],
        )
        self.expire(attempt, now=now)
        recover_expired_attempts(now=now)
        state = DataReleaseStagingState.objects.get(attempt=attempt)
        self.assertEqual(state.status, DataReleaseStagingState.Status.CLEANUP_PENDING)
        self.assertEqual(StagedWatershed.objects.count(), 1)

        state.retention_until = now - timedelta(seconds=1)
        state.save(update_fields=("retention_until", "updated_at"))

        def fail_cleanup():
            raise RuntimeError("token=example-value synthetic cleanup failure")

        failed = cleanup_staging(attempt, now=now, fault=fail_cleanup)
        state.refresh_from_db()
        self.assertEqual(failed.status, "pending")
        self.assertNotIn("example-value", failed.error)
        self.assertEqual(state.cleanup_attempts, 1)
        self.assertEqual(StagedWatershed.objects.count(), 1)

        retried = retry_pending_cleanup(now=now)
        state.refresh_from_db()
        self.assertEqual(retried[0].status, "cleaned")
        self.assertEqual(state.cleanup_attempts, 2)
        self.assertEqual(state.status, DataReleaseStagingState.Status.CLEANED)
        self.assertEqual(StagedWatershed.objects.count(), 0)

    def test_recovery_preserves_active_serving_and_persistent_state(self):
        now = timezone.now()
        collection, identity, active_release, run_state, capability = create_release(
            1,
            capability=True,
        )
        activation_attempt = begin_attempt(active_release)
        activation_attempt = transition_attempt(
            activation_attempt,
            DataReleaseAttempt.Status.STAGING,
        )
        activation_attempt = transition_attempt(
            activation_attempt,
            DataReleaseAttempt.Status.APPLYING,
            actual_plan_sha256=activation_attempt.reviewed_plan_sha256,
        )
        activate_release(activation_attempt)
        watershed = Watershed.objects.create(
            runid=run_state.runid,
            logical_watershed=identity,
            geom=GEOSGeometry(GEOMETRY),
        )
        Subcatchment.objects.create(
            watershed=watershed,
            logical_watershed=identity,
            topazid=1,
            weppid=1,
            geom=GEOSGeometry(GEOMETRY),
        )
        Channel.objects.create(
            watershed=watershed,
            logical_watershed=identity,
            topazid=1,
            weppid=1,
            order=1,
            geom=GEOSGeometry(GEOMETRY),
        )
        get_user_model().objects.create_user(username="db16-operator")
        Session.objects.create(
            session_key="db16-session",
            session_data="e30:synthetic",
            expire_date=now + timedelta(hours=1),
        )

        _, _, successor, successor_run, _ = create_release(
            2,
            identity=identity,
            collection=collection,
            previous=active_release,
        )
        staging_attempt = begin_staging(successor)
        open_loading(
            staging_attempt,
            retention_until=now - timedelta(seconds=1),
        )
        load_staging_rows(
            staging_attempt,
            watersheds=[watershed_values(successor_run, identity)],
        )
        before = {
            "watersheds": Watershed.objects.count(),
            "subcatchments": Subcatchment.objects.count(),
            "channels": Channel.objects.count(),
            "users": get_user_model().objects.count(),
            "sessions": Session.objects.count(),
            "active": ActiveDataRelease.objects.get(singleton_id=1).release_id,
            "visible_capabilities": list(
                RunCapability.objects.visible().values_list("pk", flat=True)
            ),
        }
        self.expire(staging_attempt, now=now)
        recover_expired_attempts(now=now)
        after = {
            "watersheds": Watershed.objects.count(),
            "subcatchments": Subcatchment.objects.count(),
            "channels": Channel.objects.count(),
            "users": get_user_model().objects.count(),
            "sessions": Session.objects.count(),
            "active": ActiveDataRelease.objects.get(singleton_id=1).release_id,
            "visible_capabilities": list(
                RunCapability.objects.visible().values_list("pk", flat=True)
            ),
        }
        self.assertEqual(after, before)
        self.assertEqual(before["visible_capabilities"], [capability.pk])
        self.assertFalse(StagedWatershed.objects.exists())
