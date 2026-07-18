import json

from django.core.management.base import BaseCommand, CommandError

from server.watershed.legacy_base import (
    LegacyBaseError,
    load_legacy_baseline,
    rollback_legacy_adoption,
)


class Command(BaseCommand):
    help = "Roll back one exact adopted legacy baseline to EMPTY."

    def add_arguments(self, parser):
        parser.add_argument("--root", required=True)
        parser.add_argument("--manifest-sha256", required=True)

    def handle(self, *args, **options):
        try:
            baseline = load_legacy_baseline(
                options["root"], options["manifest_sha256"]
            )
            release = rollback_legacy_adoption(baseline)
        except LegacyBaseError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            json.dumps(
                {"status": "rolled-back", "release_id": release.release_id},
                sort_keys=True,
            )
        )
