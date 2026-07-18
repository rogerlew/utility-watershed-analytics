import json

from django.core.management.base import BaseCommand, CommandError

from server.watershed.legacy_base import (
    LegacyBaseError,
    adopt_legacy_base,
    load_legacy_baseline,
)


class Command(BaseCommand):
    help = "Adopt one exact reviewed unmanaged legacy baseline."

    def add_arguments(self, parser):
        parser.add_argument("--root", required=True)
        parser.add_argument("--manifest-sha256", required=True)
        parser.add_argument("--actor", required=True)
        parser.add_argument("--application-git-commit", required=True)
        parser.add_argument("--reviewed-plan-sha256", required=True)

    def handle(self, *args, **options):
        try:
            baseline = load_legacy_baseline(
                options["root"], options["manifest_sha256"]
            )
            release = adopt_legacy_base(
                baseline,
                actor_identifier=options["actor"],
                application_git_commit=options["application_git_commit"],
                reviewed_plan_sha256=options["reviewed_plan_sha256"],
            )
        except LegacyBaseError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            json.dumps(
                {"status": "adopted", "release_id": release.release_id},
                sort_keys=True,
            )
        )
