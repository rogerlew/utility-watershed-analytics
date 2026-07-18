import json

from django.core.management.base import BaseCommand

from server.watershed.staging import recover_expired_attempts


class Command(BaseCommand):
    help = "Fail expired release attempts and apply their staging retention policy."

    def handle(self, *args, **options):
        recovered = recover_expired_attempts()
        self.stdout.write(
            json.dumps(
                {
                    "status": "recovered",
                    "attempts": [
                        {
                            "attempt_id": str(attempt_id),
                            "prior_status": prior_status,
                            "cleanup": cleanup,
                        }
                        for attempt_id, prior_status, cleanup in recovered
                    ],
                },
                sort_keys=True,
            )
        )
