import hashlib
import threading
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from server.watershed.domain_mutations import (
    ReconciliationError,
    apply_staged_release,
)
from server.watershed.fingerprint_contract import canonical_sha256
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
    WatershedRunAlias,
)
from server.watershed.planner import plan_forward
from server.watershed.planner import PlanningError
from server.watershed.release_ledger import begin_release_attempt, transition_attempt
from server.watershed.release_validation import compute_serving_fingerprints
from server.watershed.staging_models import (
    DataReleaseStagingState,
    StagedChannel,
    StagedRunCapability,
    StagedSubcatchment,
    StagedWatershed,
)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def geometry(offset, size=1):
    return MultiPolygon(
        Polygon(
            (
                (offset, 0),
                (offset + size, 0),
                (offset + size, size),
                (offset, size),
                (offset, 0),
            ),
            srid=4326,
        ),
        srid=4326,
    )


class AtomicReconcilerTests(TransactionTestCase):
    reset_sequences = True
    migration = "watershed.0011_capability_runtime_types"

    def setUp(self):
        super().setUp()
        MigrationExecutor(connection).migrate(
            [("watershed", "0011_capability_runtime_types")]
        )

    def _post_teardown(self):
        super()._post_teardown()
        ActiveDataRelease.objects.get_or_create(singleton_id=1)

    def release(self, release_id, suffix, counts):
        return DataRelease.objects.create(
            release_id=release_id,
            manifest_sha256=digest(f"manifest-{suffix}"),
            release_fingerprint=digest(f"release-{suffix}"),
            domain_fingerprint=digest(f"domain-{suffix}"),
            supported_migration=self.migration,
            materializer_image_digest=f"sha256:{digest('shared-image')}",
            materializer_git_commit=digest("shared-git")[:40],
            expected_watersheds=counts[0],
            expected_subcatchments=counts[1],
            expected_channels=counts[2],
            actual_watersheds=counts[0],
            actual_subcatchments=counts[1],
            actual_channels=counts[2],
            validation_summary={"synthetic": True},
            created_at=timezone.now(),
        )

    def identity(self, key):
        collection, _ = WatershedCollection.objects.get_or_create(key="db23")
        identity, _ = WatershedIdentity.objects.get_or_create(
            watershed_key=key,
            defaults={"collection": collection},
        )
        return identity

    def run_state(
        self,
        release,
        key,
        runid,
        *,
        metadata="same",
        geometry_value="same",
        children="same",
        capability=None,
        subcatchments=1,
    ):
        identity = self.identity(key)
        return DataRunState.objects.create(
            release=release,
            collection=identity.collection,
            watershed_identity=identity,
            runid=runid,
            run_fingerprint=digest(
                f"{runid}:{metadata}:{geometry_value}:{children}:{capability}"
            ),
            metadata_fingerprint=digest(f"metadata-{metadata}"),
            geometry_fingerprint=digest(f"geometry-{geometry_value}"),
            subcatchment_fingerprint=digest(f"subcatchment-{children}"),
            channel_fingerprint=digest(f"channel-{children}"),
            hillslope_fingerprint=digest(f"hillslope-{children}"),
            soil_fingerprint=digest(f"soil-{children}"),
            landuse_fingerprint=digest(f"landuse-{children}"),
            capability_fingerprint=digest(capability) if capability else None,
            actual_subcatchments=subcatchments,
            actual_channels=1,
        )

    def capability_values(self, fingerprint, suffix):
        base_uri = f"https://artifacts.example.test/{suffix}/"
        index_uri = f"{base_uri}index.json"
        index_sha = digest(f"index-{suffix}")
        return {
            "capability_type": RunCapability.CapabilityType.SBS,
            "mode": RunCapability.Mode.PRECOMPUTED,
            "durable_base_uri": base_uri,
            "index_uri": index_uri,
            "index_sha256": index_sha,
            "capability_fingerprint": fingerprint,
            "runtime_configuration": {
                "schema_version": 1,
                "enabled": True,
                "access_policy": "public",
                "index_uri": index_uri,
                "index_sha256": index_sha,
                "geometry_revision": digest(f"geometry-{suffix}"),
                "artifact": {
                    "uri": f"{base_uri}severity.tif",
                    "sha256": digest(f"artifact-{suffix}"),
                    "bytes": 4096,
                    "media_type": "image/tiff",
                    "verified": True,
                },
            },
        }

    def serve_run(self, state, offset, *, subcatchments=None):
        WatershedRunAlias.objects.create(
            runid=state.runid,
            watershed_identity=state.watershed_identity,
            is_current=True,
        )
        watershed = Watershed.objects.create(
            runid=state.runid,
            logical_watershed=state.watershed_identity,
            srcname=f"old-{state.watershed_identity.watershed_key}",
            geom=geometry(offset),
            simplified_geom=geometry(offset, 0.8),
        )
        keys = subcatchments or range(1, state.actual_subcatchments + 1)
        for topazid in keys:
            Subcatchment.objects.create(
                watershed=watershed,
                logical_watershed=state.watershed_identity,
                topazid=topazid,
                weppid=100 + topazid,
                slope_scalar=topazid / 10,
                geom=geometry(offset + topazid / 10, 0.1),
            )
        Channel.objects.create(
            watershed=watershed,
            logical_watershed=state.watershed_identity,
            topazid=1,
            weppid=201,
            order=1,
            geom=geometry(offset + 0.5, 0.1),
        )
        return watershed

    def stage_run(
        self,
        attempt,
        state,
        offset,
        *,
        source_name=None,
        subcatchments=None,
        capability_suffix=None,
    ):
        staged = StagedWatershed.objects.create(
            attempt=attempt,
            run_state=state,
            watershed_identity=state.watershed_identity,
            source_fingerprint=state.run_fingerprint,
            validation_status=StagedWatershed.ValidationStatus.VALIDATED,
            runid=state.runid,
            geom=geometry(offset),
            metadata={"srcname": source_name or f"old-{state.watershed_identity.watershed_key}"},
        )
        keys = subcatchments or range(1, state.actual_subcatchments + 1)
        for topazid in keys:
            StagedSubcatchment.objects.create(
                attempt=attempt,
                run_state=state,
                watershed_identity=state.watershed_identity,
                source_fingerprint=state.subcatchment_fingerprint,
                validation_status=StagedSubcatchment.ValidationStatus.VALIDATED,
                topazid=topazid,
                weppid=100 + topazid,
                geom=geometry(offset + topazid / 10, 0.1),
                attributes={"slope_scalar": topazid / 5},
            )
        StagedChannel.objects.create(
            attempt=attempt,
            run_state=state,
            watershed_identity=state.watershed_identity,
            source_fingerprint=state.channel_fingerprint,
            validation_status=StagedChannel.ValidationStatus.VALIDATED,
            topazid=1,
            weppid=201,
            order=1,
            geom=geometry(offset + 0.6, 0.1),
        )
        if capability_suffix:
            values = self.capability_values(
                state.capability_fingerprint,
                capability_suffix,
            )
            StagedRunCapability.objects.create(
                attempt=attempt,
                run_state=state,
                watershed_identity=state.watershed_identity,
                source_fingerprint=state.capability_fingerprint,
                validation_status=StagedRunCapability.ValidationStatus.VALIDATED,
                **values,
            )
        return staged

    def snapshot(self):
        return {
            "active": list(
                ActiveDataRelease.objects.values_list(
                    "state", "release_id", "manifest_sha256", "activated_at"
                )
            ),
            "watersheds": list(
                Watershed.objects.order_by("runid").values_list(
                    "runid", "logical_watershed_id", "srcname", "geom", "simplified_geom"
                )
            ),
            "subcatchments": list(
                Subcatchment.objects.order_by("pk").values_list(
                    "pk", "watershed_id", "logical_watershed_id", "topazid", "weppid"
                )
            ),
            "channels": list(
                Channel.objects.order_by("pk").values_list(
                    "pk", "watershed_id", "logical_watershed_id", "topazid", "weppid", "order"
                )
            ),
            "identities": list(
                WatershedIdentity.objects.order_by("watershed_key").values_list(
                    "watershed_key", "status"
                )
            ),
            "aliases": list(
                WatershedRunAlias.objects.order_by("runid").values_list(
                    "runid", "watershed_identity_id", "is_current"
                )
            ),
            "capabilities": list(
                RunCapability.objects.order_by("pk").values_list(
                    "run_state_id", "watershed_identity_id", "capability_fingerprint"
                )
            ),
        }

    def prepare(self):
        base = self.release("2026-07-18.230", "base", (4, 5, 4))
        base_states = {
            "alpha": self.run_state(
                base,
                "alpha",
                "alpha-v1",
                metadata="old",
                geometry_value="old",
                children="old",
                capability="old-capability",
                subcatchments=2,
            ),
            "beta": self.run_state(base, "beta", "beta-v1"),
            "replacement": self.run_state(base, "replacement", "replace-v1"),
            "removed": self.run_state(base, "removed", "removed-v1"),
        }
        offsets = {"alpha": 1, "beta": 4, "replacement": 7, "removed": 10}
        for key, state in base_states.items():
            self.serve_run(state, offsets[key])
        old_capability = self.capability_values(
            base_states["alpha"].capability_fingerprint,
            "old-capability",
        )
        RunCapability.objects.create(
            run_state=base_states["alpha"],
            watershed_identity=base_states["alpha"].watershed_identity,
            **old_capability,
        )
        observed_base = compute_serving_fingerprints(base)
        DataRelease.objects.filter(pk=base.pk).update(
            domain_fingerprint=observed_base.domain,
            status=DataRelease.Status.ACTIVE,
        )
        base.refresh_from_db()
        active, _ = ActiveDataRelease.objects.get_or_create(singleton_id=1)
        active.state = ActiveDataRelease.State.ACTIVE
        active.release = base
        active.manifest_sha256 = base.manifest_sha256
        active.data_contract = 1
        active.activated_at = timezone.now()
        active._allow_activation_change = True
        active.save()

        target = self.release("2026-07-18.231", "target", (4, 5, 4))
        target_states = {
            "alpha": self.run_state(
                target,
                "alpha",
                "alpha-v1",
                metadata="new",
                geometry_value="new",
                children="new",
                capability="new-capability",
                subcatchments=2,
            ),
            "added": self.run_state(target, "added", "added-v1"),
            "beta": self.run_state(target, "beta", "beta-v1"),
            "replacement": self.run_state(target, "replacement", "replace-v2"),
        }
        initial_plan = plan_forward(base, target, allow_large_removals=True)
        initial_digest = canonical_sha256(initial_plan)
        attempt = begin_release_attempt(
            release=target,
            actor_kind=DataReleaseAttempt.ActorKind.OPERATOR,
            actor_identifier="db23-test",
            target_environment="test",
            application_git_commit=digest("application")[:40],
            reviewed_plan_sha256=initial_digest,
            lease_owner="forest1:db23-test",
        )
        attempt = transition_attempt(attempt, DataReleaseAttempt.Status.STAGING)
        self.stage_run(
            attempt,
            target_states["alpha"],
            2,
            source_name="new-alpha",
            subcatchments=(1, 3),
            capability_suffix="new-capability",
        )
        self.stage_run(attempt, target_states["added"], 13)
        self.stage_run(attempt, target_states["beta"], 4)
        self.stage_run(attempt, target_states["replacement"], 7)
        DataReleaseStagingState.objects.create(
            attempt=attempt,
            status=DataReleaseStagingState.Status.READY,
            artifact_bytes=1,
            staging_bytes=1,
            index_bytes=1,
            backup_bytes=1,
            wal_bytes=1,
            margin_bytes=1,
            available_bytes=10,
            watershed_rows=4,
            subcatchment_rows=5,
            channel_rows=4,
            capability_rows=1,
            retention_until=timezone.now() + timedelta(hours=1),
        )
        attempt = transition_attempt(
            attempt,
            DataReleaseAttempt.Status.APPLYING,
            actual_plan_sha256=initial_digest,
        )

        captured = []
        original_compute = compute_serving_fingerprints

        def capture_target(release):
            observed = original_compute(release)
            captured.append(observed)
            return replace(observed, domain=release.domain_fingerprint)

        with transaction.atomic():
            savepoint = transaction.savepoint()
            with patch(
                "server.watershed.release_validation.compute_serving_fingerprints",
                side_effect=capture_target,
            ):
                apply_staged_release(attempt, initial_plan)
            transaction.savepoint_rollback(savepoint)
        DataRelease.objects.filter(pk=target.pk).update(
            domain_fingerprint=captured[-1].domain
        )
        base.refresh_from_db()
        target.refresh_from_db()
        attempt.refresh_from_db()
        final_plan = plan_forward(base, target, allow_large_removals=True)
        final_digest = canonical_sha256(final_plan)
        DataReleaseAttempt.objects.filter(pk=attempt.pk).update(
            reviewed_plan_sha256=final_digest,
            actual_plan_sha256=final_digest,
        )
        attempt.refresh_from_db()
        return base, target, attempt, final_plan

    def test_reconciles_exact_scope_and_preserves_retained_public_ids(self):
        base, target, attempt, plan = self.prepare()
        alpha = self.identity("alpha")
        beta = self.identity("beta")
        replacement = self.identity("replacement")
        alpha_subcatchment_id = Subcatchment.objects.get(
            logical_watershed=alpha,
            topazid=1,
        ).pk
        alpha_channel_id = Channel.objects.get(logical_watershed=alpha).pk
        replacement_subcatchment_id = Subcatchment.objects.get(
            logical_watershed=replacement
        ).pk
        beta_snapshot = list(
            Watershed.objects.filter(logical_watershed=beta).values()
        )
        unrelated_count = ContentType.objects.count()

        result = apply_staged_release(attempt, plan, batch_size=2)

        self.assertEqual((result.added, result.changed, result.removed, result.retained), (1, 2, 1, 1))
        self.assertEqual(ActiveDataRelease.objects.get().release_id, target.release_id)
        self.assertEqual(
            Subcatchment.objects.get(logical_watershed=alpha, topazid=1).pk,
            alpha_subcatchment_id,
        )
        self.assertEqual(Channel.objects.get(logical_watershed=alpha).pk, alpha_channel_id)
        self.assertFalse(Subcatchment.objects.filter(logical_watershed=alpha, topazid=2).exists())
        self.assertTrue(Subcatchment.objects.filter(logical_watershed=alpha, topazid=3).exists())
        alpha_watershed = Watershed.objects.get(logical_watershed=alpha)
        self.assertEqual(alpha_watershed.srcname, "new-alpha")
        self.assertIsNotNone(alpha_watershed.simplified_geom)
        self.assertEqual(
            Subcatchment.objects.get(logical_watershed=replacement).pk,
            replacement_subcatchment_id,
        )
        self.assertEqual(Watershed.objects.get(logical_watershed=replacement).runid, "replace-v2")
        self.assertFalse(WatershedRunAlias.objects.get(runid="replace-v1").is_current)
        self.assertTrue(WatershedRunAlias.objects.get(runid="replace-v2").is_current)
        self.assertFalse(Watershed.objects.filter(logical_watershed__watershed_key="removed").exists())
        self.assertEqual(self.identity("removed").status, WatershedIdentity.Status.RETIRED)
        self.assertTrue(Watershed.objects.filter(logical_watershed__watershed_key="added").exists())
        self.assertEqual(
            list(Watershed.objects.filter(logical_watershed=beta).values()),
            beta_snapshot,
        )
        self.assertEqual(ContentType.objects.count(), unrelated_count)
        self.assertEqual(
            RunCapability.objects.filter(run_state__release=target).count(),
            1,
        )
        self.assertEqual(
            RunCapability.objects.filter(run_state__release=base).count(),
            1,
        )
        self.assertEqual(compute_serving_fingerprints(target).domain, target.domain_fingerprint)
        self.assertEqual(DataReleaseAttempt.objects.get(pk=attempt.pk).status, DataReleaseAttempt.Status.SUCCEEDED)
        self.assertEqual(DataRelease.objects.get(pk=base.pk).status, DataRelease.Status.SUPERSEDED)

    def test_wrong_plan_staging_and_injected_failure_leave_base_unchanged(self):
        _, _, attempt, plan = self.prepare()
        original = self.snapshot()
        wrong_plan = {**plan, "plan_id": "wrong-plan"}
        with self.assertRaisesRegex(ReconciliationError, "digests differ"):
            apply_staged_release(attempt, wrong_plan)
        self.assertEqual(self.snapshot(), original)

        active = ActiveDataRelease.objects.get()
        ActiveDataRelease.objects.filter(pk=active.pk).update(
            manifest_sha256=digest("wrong-active-manifest")
        )
        with self.assertRaisesRegex(PlanningError, "Active base differs"):
            apply_staged_release(attempt, plan)
        ActiveDataRelease.objects.filter(pk=active.pk).update(
            manifest_sha256=attempt.previous_active_release.manifest_sha256
        )
        self.assertEqual(self.snapshot(), original)

        DataReleaseStagingState.objects.filter(attempt=attempt).update(
            status=DataReleaseStagingState.Status.LOADING
        )
        with self.assertRaisesRegex(ReconciliationError, "READY staging"):
            apply_staged_release(attempt, plan)
        DataReleaseStagingState.objects.filter(attempt=attempt).update(
            status=DataReleaseStagingState.Status.READY
        )
        self.assertEqual(self.snapshot(), original)

        with patch(
            "server.watershed.domain_mutations._replace_target_capabilities",
            side_effect=RuntimeError("injected before pointer advance"),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                apply_staged_release(attempt, plan)
        self.assertEqual(self.snapshot(), original)

    def test_concurrent_reader_observes_old_then_complete_new_state(self):
        base, target, attempt, plan = self.prepare()
        paused = threading.Event()
        release = threading.Event()
        failures = []
        original_replace = __import__(
            "server.watershed.domain_mutations",
            fromlist=["_replace_target_capabilities"],
        )._replace_target_capabilities

        def pause_before_pointer(*args, **kwargs):
            paused.set()
            if not release.wait(timeout=10):
                raise RuntimeError("reader proof timed out")
            return original_replace(*args, **kwargs)

        def writer():
            close_old_connections()
            try:
                apply_staged_release(
                    DataReleaseAttempt.objects.get(pk=attempt.pk),
                    plan,
                )
            except Exception as error:
                failures.append(error)
            finally:
                close_old_connections()

        with patch(
            "server.watershed.domain_mutations._replace_target_capabilities",
            side_effect=pause_before_pointer,
        ):
            thread = threading.Thread(target=writer)
            thread.start()
            self.assertTrue(paused.wait(timeout=10))
            self.assertEqual(ActiveDataRelease.objects.get().release_id, base.release_id)
            self.assertEqual(Watershed.objects.get(logical_watershed__watershed_key="alpha").srcname, "old-alpha")
            self.assertTrue(Watershed.objects.filter(logical_watershed__watershed_key="removed").exists())
            self.assertFalse(Watershed.objects.filter(logical_watershed__watershed_key="added").exists())
            release.set()
            thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(ActiveDataRelease.objects.get().release_id, target.release_id)
        self.assertEqual(Watershed.objects.get(logical_watershed__watershed_key="alpha").srcname, "new-alpha")
        self.assertFalse(Watershed.objects.filter(logical_watershed__watershed_key="removed").exists())
        self.assertTrue(Watershed.objects.filter(logical_watershed__watershed_key="added").exists())
