import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from server.watershed.models import DataRelease
from server.watershed.planner import (
    PlanningError,
    plan_bytes,
    plan_empty_build,
    plan_exact_inverse,
    plan_forward,
)


class Command(BaseCommand):
    help = "Generate reviewed-base forward, inverse, and EMPTY-build plans."

    def add_arguments(self, parser):
        parser.add_argument("--base-release-id", required=True)
        parser.add_argument("--target-release-id", required=True)
        parser.add_argument("--output-directory", required=True)
        parser.add_argument("--allow-large-removals", action="store_true")

    def handle(self, *args, **options):
        try:
            base = DataRelease.objects.get(release_id=options["base_release_id"])
            target = DataRelease.objects.get(release_id=options["target_release_id"])
            forward = plan_forward(
                base,
                target,
                allow_large_removals=options["allow_large_removals"],
            )
            plans = {
                "forward.json": forward,
                "exact-inverse.json": plan_exact_inverse(forward),
                "empty-build.json": plan_empty_build(target),
            }
            output_directory = Path(options["output_directory"])
            output_directory.mkdir(parents=True, exist_ok=True)
            paths = [output_directory / name for name in plans]
            if any(path.exists() for path in paths):
                raise PlanningError("Plan output already exists; refusing overwrite.")
            for path, plan in zip(paths, plans.values(), strict=True):
                path.write_bytes(plan_bytes(plan))
        except (DataRelease.DoesNotExist, OSError, PlanningError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            json.dumps(
                {
                    "status": "generated",
                    "base_release_id": base.release_id,
                    "target_release_id": target.release_id,
                    "output_directory": str(output_directory),
                },
                sort_keys=True,
            )
        )
