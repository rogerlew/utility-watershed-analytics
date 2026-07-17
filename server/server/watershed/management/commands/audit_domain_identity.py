import json

from django.core.management.base import BaseCommand, CommandError

from server.watershed.identity_audit import build_identity_audit_report


class Command(BaseCommand):
    help = "Audit watershed-domain identities using aggregate read-only queries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-violations",
            action="store_true",
            help="Exit non-zero when duplicate business keys or orphans exist",
        )

    def handle(self, *args, **options):
        report = build_identity_audit_report()
        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        if options["fail_on_violations"] and report["violations"]:
            raise CommandError("Domain identity audit found violations")
