from django.contrib.gis.geos import GEOSGeometry
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


GEOMETRY = "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"


class StableIdentityMigrationTests(TransactionTestCase):
    migrate_from = [("watershed", "0006_watershed_utility_metadata")]
    migrate_to = [("watershed", "0007_stable_watershed_identity")]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        Watershed = old_apps.get_model("watershed", "Watershed")
        Subcatchment = old_apps.get_model("watershed", "Subcatchment")
        Channel = old_apps.get_model("watershed", "Channel")

        gate = Watershed.objects.create(
            runid="aversive-forestry",
            geom=GEOSGeometry(GEOMETRY),
        )
        batch = Watershed.objects.create(
            runid="batch;;nasa-roses-2026-sbs;;OR-20",
            geom=GEOSGeometry(GEOMETRY),
        )
        self.subcatchment_id = Subcatchment.objects.create(
            watershed=gate,
            topazid=1,
            weppid=2,
            geom=GEOSGeometry(GEOMETRY),
        ).pk
        self.channel_id = Channel.objects.create(
            watershed=batch,
            topazid=3,
            weppid=4,
            order=1,
            geom=GEOSGeometry(GEOMETRY),
        ).pk

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.migrate_to)
        super().tearDown()

    def test_forward_backfills_exact_assignments_aliases_and_children(self):
        Watershed = self.apps.get_model("watershed", "Watershed")
        WatershedIdentity = self.apps.get_model("watershed", "WatershedIdentity")
        WatershedRunAlias = self.apps.get_model("watershed", "WatershedRunAlias")
        Subcatchment = self.apps.get_model("watershed", "Subcatchment")
        Channel = self.apps.get_model("watershed", "Channel")

        gate = Watershed.objects.get(runid="aversive-forestry")
        batch = Watershed.objects.get(runid="batch;;nasa-roses-2026-sbs;;OR-20")

        self.assertEqual(gate.logical_watershed.watershed_key, "gate-creek")
        self.assertEqual(gate.logical_watershed.collection_id, "gate-creek")
        self.assertIsNone(batch.logical_watershed.watershed_key)
        self.assertEqual(batch.logical_watershed.collection_id, "nasa-roses")
        self.assertEqual(WatershedIdentity.objects.count(), 2)
        self.assertEqual(WatershedRunAlias.objects.filter(is_current=True).count(), 2)
        self.assertEqual(
            Subcatchment.objects.get(pk=self.subcatchment_id).logical_watershed_id,
            gate.logical_watershed_id,
        )
        self.assertEqual(
            Channel.objects.get(pk=self.channel_id).logical_watershed_id,
            batch.logical_watershed_id,
        )

    def test_old_model_state_reads_expanded_schema(self):
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        OldWatershed = old_apps.get_model("watershed", "Watershed")
        self.assertEqual(OldWatershed.objects.count(), 2)
        self.assertEqual(
            OldWatershed.objects.get(pk="aversive-forestry").runid,
            "aversive-forestry",
        )

    def test_pre_write_rollback_preserves_old_rows_and_child_ids(self):
        reverse_executor = MigrationExecutor(connection)
        reverse_executor.migrate(self.migrate_from)
        old_apps = reverse_executor.loader.project_state(self.migrate_from).apps
        Watershed = old_apps.get_model("watershed", "Watershed")
        Subcatchment = old_apps.get_model("watershed", "Subcatchment")
        Channel = old_apps.get_model("watershed", "Channel")

        self.assertEqual(Watershed.objects.count(), 2)
        self.assertTrue(Subcatchment.objects.filter(pk=self.subcatchment_id).exists())
        self.assertTrue(Channel.objects.filter(pk=self.channel_id).exists())

    def test_rollback_closes_after_identity_aware_alias_write(self):
        Watershed = self.apps.get_model("watershed", "Watershed")
        WatershedRunAlias = self.apps.get_model("watershed", "WatershedRunAlias")
        gate = Watershed.objects.get(runid="aversive-forestry")
        WatershedRunAlias.objects.filter(
            watershed_identity_id=gate.logical_watershed_id
        ).update(is_current=False)
        WatershedRunAlias.objects.create(
            runid="gate-successor",
            watershed_identity_id=gate.logical_watershed_id,
            is_current=True,
        )

        with self.assertRaisesRegex(RuntimeError, "rollback is closed"):
            MigrationExecutor(connection).migrate(self.migrate_from)
