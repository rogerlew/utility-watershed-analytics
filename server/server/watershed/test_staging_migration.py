from django.contrib.gis.geos import GEOSGeometry
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


GEOMETRY = "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"


class AttemptScopedStagingMigrationTests(TransactionTestCase):
    migrate_from = [("watershed", "0009_release_ledger_capabilities")]
    migrate_to = [("watershed", "0010_attempt_scoped_staging")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        self.old_apps = executor.loader.project_state(self.migrate_from).apps
        Watershed = self.old_apps.get_model("watershed", "Watershed")
        Watershed.objects.create(
            runid="db16-existing-serving-row",
            geom=GEOSGeometry(GEOMETRY),
        )

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.migrate_to)
        super().tearDown()

    def test_forward_and_reverse_preserve_existing_serving_and_ledger(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        apps = executor.loader.project_state(self.migrate_to).apps
        Watershed = apps.get_model("watershed", "Watershed")
        ActiveDataRelease = apps.get_model("watershed", "ActiveDataRelease")
        self.assertEqual(Watershed.objects.count(), 1)
        self.assertEqual(ActiveDataRelease.objects.count(), 1)
        for model_name in (
            "DataReleaseStagingState",
            "StagedWatershed",
            "StagedSubcatchment",
            "StagedChannel",
            "StagedRunCapability",
        ):
            self.assertTrue(apps.get_model("watershed", model_name))

        MigrationExecutor(connection).migrate(self.migrate_from)
        apps = MigrationExecutor(connection).loader.project_state(self.migrate_from).apps
        Watershed = apps.get_model("watershed", "Watershed")
        ActiveDataRelease = apps.get_model("watershed", "ActiveDataRelease")
        self.assertEqual(Watershed.objects.count(), 1)
        self.assertEqual(ActiveDataRelease.objects.count(), 1)
        tables = connection.introspection.table_names()
        self.assertNotIn("watershed_stagedwatershed", tables)
        self.assertNotIn("watershed_datareleasestagingstate", tables)
