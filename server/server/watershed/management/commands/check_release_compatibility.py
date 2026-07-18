import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from server.watershed.deployment_compatibility import (
    DeploymentCompatibilityError,
    verify_release_compatibility,
)
from server.watershed.models import DataRelease, DataReleaseAttempt


class Command(BaseCommand):
    help = "Fail unless one staged release is compatible with code, schema, plan, and base."

    def add_arguments(self, parser):
        parser.add_argument("--release-id", required=True)
        parser.add_argument("--attempt-id", required=True)
        parser.add_argument("--plan-file", required=True)
        parser.add_argument("--expected-base-manifest", required=True)
        parser.add_argument("--materializer-image-digest", required=True)
        parser.add_argument("--materializer-git-commit", required=True)
        parser.add_argument("--application-git-commit", required=True)

    def handle(self, *args, **options):
        try:
            plan_path = Path(options["plan_file"])
            if plan_path.is_symlink() or not plan_path.is_file():
                raise DeploymentCompatibilityError("Plan must be an ordinary file.")
            if plan_path.stat().st_size > 10 * 1024 * 1024:
                raise DeploymentCompatibilityError("Plan exceeds the bounded size limit.")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            if not isinstance(plan, dict):
                raise DeploymentCompatibilityError("Plan must be a JSON object.")
            release = DataRelease.objects.get(pk=options["release_id"])
            attempt = DataReleaseAttempt.objects.get(pk=options["attempt_id"])
            result = verify_release_compatibility(
                release,
                attempt,
                plan,
                expected_base_manifest=options["expected_base_manifest"],
                materializer_image_digest=options["materializer_image_digest"],
                materializer_git_commit=options["materializer_git_commit"],
                application_git_commit=options["application_git_commit"],
            )
        except (
            DataRelease.DoesNotExist,
            DataReleaseAttempt.DoesNotExist,
            DeploymentCompatibilityError,
            json.JSONDecodeError,
            OSError,
        ) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            json.dumps(
                {
                    "status": "compatible",
                    "release_id": result.release_id,
                    "active_base": result.active_base,
                    "migration": result.migration,
                    "artifact_rows": result.artifact_rows,
                    "capability_rows": result.capability_rows,
                    "plan_sha256": result.plan_sha256,
                },
                sort_keys=True,
            )
        )
