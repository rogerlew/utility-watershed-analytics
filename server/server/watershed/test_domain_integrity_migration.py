from django.contrib.gis.geos import GEOSGeometry
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


GEOMETRY = "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"


class DomainIntegrityMigrationPreflightTests(TransactionTestCase):
    migrate_from = [("watershed", "0007_stable_watershed_identity")]
    migrate_to = [("watershed", "0008_domain_integrity_constraints")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        self.apps = executor.loader.project_state(self.migrate_from).apps

    def tearDown(self):
        Subcatchment = self.apps.get_model("watershed", "Subcatchment")
        Subcatchment.objects.all().delete()
        MigrationExecutor(connection).migrate(self.migrate_to)
        super().tearDown()

    def test_duplicate_fixture_fails_before_constraint_ddl(self):
        Watershed = self.apps.get_model("watershed", "Watershed")
        Subcatchment = self.apps.get_model("watershed", "Subcatchment")
        watershed = Watershed.objects.create(
            runid="dirty-run",
            geom=GEOSGeometry(GEOMETRY),
        )
        for weppid in (1, 2):
            Subcatchment.objects.create(
                watershed=watershed,
                topazid=1,
                weppid=weppid,
                geom=GEOSGeometry(GEOMETRY),
            )

        with self.assertRaisesRegex(
            RuntimeError,
            "subcatchment_run_key=1",
        ):
            MigrationExecutor(connection).migrate(self.migrate_to)
