import json

from django.core.management.base import BaseCommand, CommandError

from server.watershed.identity_validation import build_stable_identity_report


class Command(BaseCommand):
    help = "Validate the additive stable watershed identity backfill"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-violations",
            action="store_true",
            help="Exit non-zero when logical links or current aliases are incomplete",
        )

    def handle(self, *args, **options):
        report = build_stable_identity_report()
        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        if options["fail_on_violations"] and report["status"] != "passed":
            raise CommandError("Stable watershed identity validation failed")
