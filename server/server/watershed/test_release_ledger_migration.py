from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ReleaseLedgerMigrationTests(TransactionTestCase):
    migrate_from = [("watershed", "0008_domain_integrity_constraints")]
    migrate_to = [("watershed", "0009_release_ledger_capabilities")]

    def setUp(self):
        super().setUp()
        MigrationExecutor(connection).migrate(self.migrate_from)

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.migrate_to)
        super().tearDown()

    def test_forward_bootstraps_one_empty_singleton_and_reverse_is_clean(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        apps = executor.loader.project_state(self.migrate_to).apps
        ActiveDataRelease = apps.get_model("watershed", "ActiveDataRelease")
        self.assertEqual(ActiveDataRelease.objects.count(), 1)
        active = ActiveDataRelease.objects.get(singleton_id=1)
        self.assertEqual(active.state, "EMPTY")
        self.assertIsNone(active.release_id)
        self.assertIsNone(active.manifest_sha256)

        MigrationExecutor(connection).migrate(self.migrate_from)
        tables = connection.introspection.table_names()
        self.assertNotIn("watershed_activedatarelease", tables)
        self.assertNotIn("watershed_datarelease", tables)
        self.assertNotIn("watershed_runcapability", tables)
