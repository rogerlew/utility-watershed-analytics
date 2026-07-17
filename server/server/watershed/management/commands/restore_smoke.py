import json

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test import Client
from django.urls import reverse

from server.watershed.models import Channel, Subcatchment, Watershed


class Command(BaseCommand):
    help = "Run database and read-only API smoke checks after an isolated restore"

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-empty",
            action="store_true",
            help="Permit a restored database with no watershed rows",
        )

    def handle(self, *args, **options):
        call_command("check", verbosity=0)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone() != (1,):
                raise CommandError("Database connectivity check failed")

        watershed_count = Watershed.objects.count()
        subcatchment_count = Subcatchment.objects.count()
        channel_count = Channel.objects.count()
        if watershed_count == 0 and not options["allow_empty"]:
            raise CommandError("Restored database contains no watersheds")

        allowed_host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
        client = Client(HTTP_HOST=allowed_host)
        checked_endpoints = []
        self._require_success(client, reverse("watershed-list"), checked_endpoints)

        representative_runid = None
        representative = Watershed.objects.order_by("runid").first()
        if representative is not None:
            representative_runid = representative.runid
            self._require_success(
                client,
                reverse("watershed-detail", kwargs={"pk": representative.runid}),
                checked_endpoints,
            )
            self._require_success(
                client,
                reverse(
                    "watershed-subcatchments",
                    kwargs={"runid": representative.runid},
                ),
                checked_endpoints,
            )
            self._require_success(
                client,
                reverse("watershed-channels", kwargs={"runid": representative.runid}),
                checked_endpoints,
            )

        report = {
            "channel_count": channel_count,
            "database_connectivity": "passed",
            "endpoints_checked": checked_endpoints,
            "representative_runid": representative_runid,
            "subcatchment_count": subcatchment_count,
            "watershed_count": watershed_count,
        }
        self.stdout.write(json.dumps(report, sort_keys=True))

    @staticmethod
    def _require_success(client, path, checked_endpoints):
        response = client.get(path)
        if response.status_code != 200:
            raise CommandError(
                f"Restored API smoke check failed: path={path} "
                f"status={response.status_code}"
            )
        checked_endpoints.append(path)
