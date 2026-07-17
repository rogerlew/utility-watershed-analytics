import json
from io import StringIO

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from server.watershed.models import Watershed


class RestoreSmokeCommandTests(TestCase):
    def test_empty_database_requires_explicit_override(self):
        with self.assertRaisesMessage(CommandError, "contains no watersheds"):
            call_command("restore_smoke", stdout=StringIO())

    def test_allow_empty_checks_database_and_list_endpoint(self):
        output = StringIO()

        call_command("restore_smoke", "--allow-empty", stdout=output)

        report = json.loads(output.getvalue().strip())
        self.assertEqual(report["database_connectivity"], "passed")
        self.assertEqual(report["watershed_count"], 0)
        self.assertEqual(report["endpoints_checked"], ["/api/watershed/"])

    def test_representative_watershed_endpoints_are_checked(self):
        watershed = Watershed.objects.create(
            runid="restore-smoke-run",
            geom=MultiPolygon(
                Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))),
                srid=4326,
            ),
        )
        output = StringIO()

        call_command("restore_smoke", stdout=output)

        report = json.loads(output.getvalue().strip())
        self.assertEqual(report["watershed_count"], 1)
        self.assertEqual(report["representative_runid"], watershed.runid)
        self.assertEqual(
            report["endpoints_checked"],
            [
                "/api/watershed/",
                "/api/watershed/restore-smoke-run/",
                "/api/watershed/restore-smoke-run/subcatchments",
                "/api/watershed/restore-smoke-run/channels",
            ],
        )
