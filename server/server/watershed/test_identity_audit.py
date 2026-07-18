import json
from io import StringIO

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from server.watershed.models import Channel, Subcatchment, Watershed


def test_geometry() -> MultiPolygon:
    return MultiPolygon(Polygon(((0, 0), (1, 0), (1, 1), (0, 0))))


class DomainIdentityAuditTests(TransactionTestCase):
    def run_audit(self, *, fail_on_violations=False):
        output = StringIO()
        call_command(
            "audit_domain_identity",
            fail_on_violations=fail_on_violations,
            stdout=output,
        )
        return json.loads(output.getvalue())

    def create_watershed(self, runid="batch;;test;;private-row-value"):
        return Watershed.objects.create(runid=runid, geom=test_geometry())

    def test_clean_report_is_deterministic_and_contains_no_row_identity(self):
        watershed = self.create_watershed()
        Subcatchment.objects.create(
            watershed=watershed,
            topazid=1,
            weppid=10,
            geom=test_geometry(),
        )
        Channel.objects.create(
            watershed=watershed,
            topazid=2,
            weppid=20,
            order=1,
            geom=test_geometry(),
        )

        first = self.run_audit()
        second = self.run_audit()

        self.assertEqual(first, second)
        self.assertEqual(first["status"], "passed")
        self.assertEqual(first["tables"]["watershed"]["row_count"], 1)
        self.assertNotIn(watershed.runid, json.dumps(first))

    def test_report_describes_current_keys_constraints_and_cascade(self):
        report = self.run_audit()

        watershed = report["tables"]["watershed"]
        self.assertEqual(watershed["business_key"], ["runid"])
        self.assertTrue(watershed["business_key_database_enforced"])

        subcatchment = report["tables"]["subcatchment"]
        self.assertEqual(
            subcatchment["business_key"],
            ["watershed_id", "topazid"],
        )
        self.assertTrue(subcatchment["business_key_database_enforced"])
        self.assertEqual(
            subcatchment["logical_business_key"],
            ["logical_watershed_id", "topazid"],
        )
        self.assertTrue(subcatchment["logical_business_key_database_enforced"])
        self.assertEqual(subcatchment["foreign_key"]["on_delete"], "CASCADE")
        self.assertTrue(subcatchment["foreign_key"]["database_enforced"])

        channel = report["tables"]["channel"]
        self.assertEqual(
            channel["business_key"],
            ["watershed_id", "topazid", "weppid", "order"],
        )
        self.assertTrue(channel["business_key_database_enforced"])
        self.assertEqual(
            channel["logical_business_key"],
            ["logical_watershed_id", "topazid", "weppid", "order"],
        )
        self.assertTrue(channel["logical_business_key_database_enforced"])

    def test_duplicate_business_keys_are_database_rejected(self):
        watershed = self.create_watershed()
        Subcatchment.objects.create(
            watershed=watershed,
            topazid=1,
            weppid=10,
            geom=test_geometry(),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subcatchment.objects.create(
                watershed=watershed,
                topazid=1,
                weppid=11,
                geom=test_geometry(),
            )
        Channel.objects.create(
            watershed=watershed,
            topazid=2,
            weppid=20,
            order=1,
            geom=test_geometry(),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Channel.objects.create(
                watershed=watershed,
                topazid=2,
                weppid=20,
                order=1,
                geom=test_geometry(),
            )

        report = self.run_audit()

        self.assertEqual(report["status"], "passed")
        self.assertEqual(
            report["tables"]["subcatchment"]["duplicate_business_key"],
            {"groups": 0, "rows": 0},
        )
        self.assertEqual(
            report["tables"]["channel"]["duplicate_business_key"],
            {"groups": 0, "rows": 0},
        )
        self.run_audit(fail_on_violations=True)

    def test_audit_executes_no_data_definition_or_mutation_queries(self):
        with CaptureQueriesContext(connection) as queries:
            self.run_audit()

        prohibited = ("ALTER ", "CREATE ", "DELETE ", "DROP ", "INSERT ", "TRUNCATE ", "UPDATE ")
        statements = [query["sql"].lstrip().upper() for query in queries]
        self.assertFalse(
            [statement for statement in statements if statement.startswith(prohibited)]
        )
        self.assertIn("SET TRANSACTION READ ONLY", statements)
