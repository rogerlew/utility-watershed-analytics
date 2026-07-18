import json

from django.core.management.base import BaseCommand, CommandError

from server.watershed.deployment_compatibility import (
    DeploymentCompatibilityError,
    verify_application_compatibility,
)


class Command(BaseCommand):
    help = "Fail unless the applied schema and active release are compatible with this code."

    def handle(self, *args, **options):
        try:
            result = verify_application_compatibility()
        except DeploymentCompatibilityError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            json.dumps(
                {
                    "status": "compatible",
                    "active_state": result.active_state,
                    "active_release_id": result.active_release_id,
                    "migration": result.migration,
                },
                sort_keys=True,
            )
        )
