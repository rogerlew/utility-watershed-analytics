#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime


RELEASE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


def restic_command(*arguments: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    restic_bin = os.environ.get("RESTIC_BIN", "restic")
    return subprocess.run(
        [restic_bin, *arguments],
        check=True,
        capture_output=capture_output,
        text=True,
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply time retention and exact release-point retention to restic backups."
    )
    parser.add_argument("--retain-release", action="append", default=[])
    parser.add_argument("--keep-daily", type=int, default=14)
    parser.add_argument("--keep-weekly", type=int, default=8)
    parser.add_argument("--minimum-release-points", type=int, default=3)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--prune", action="store_true")
    return parser.parse_args()


def validate_arguments(arguments: argparse.Namespace) -> None:
    for value_name in ("keep_daily", "keep_weekly", "minimum_release_points"):
        if getattr(arguments, value_name) < 1:
            raise SystemExit(f"{value_name.replace('_', '-')} must be positive")
    retained = arguments.retain_release
    if len(retained) != len(set(retained)):
        raise SystemExit("--retain-release values must be unique")
    if any(not RELEASE_PATTERN.fullmatch(release_id) for release_id in retained):
        raise SystemExit("a retained release ID contains unsupported tag characters")
    if retained and len(retained) < arguments.minimum_release_points:
        raise SystemExit(
            "release-point pruning requires the active release plus at least two rollback releases"
        )
    if arguments.prune and not arguments.apply:
        raise SystemExit("--prune requires --apply")


def load_snapshots() -> list[dict[str, object]]:
    completed = restic_command("snapshots", "--json", "--tag", "uwa-database", capture_output=True)
    return json.loads(completed.stdout)


def release_id_for_snapshot(snapshot: dict[str, object]) -> str | None:
    release_tags = [
        tag.removeprefix("release:")
        for tag in snapshot.get("tags", [])
        if isinstance(tag, str) and tag.startswith("release:")
    ]
    if len(release_tags) > 1:
        raise SystemExit(f"snapshot {snapshot['short_id']} has multiple release tags")
    return release_tags[0] if release_tags else None


def release_forget_ids(
    snapshots: list[dict[str, object]], retained_releases: set[str]
) -> list[str]:
    by_release: dict[str, list[dict[str, object]]] = defaultdict(list)
    for snapshot in snapshots:
        release_id = release_id_for_snapshot(snapshot)
        if release_id:
            by_release[release_id].append(snapshot)

    missing = retained_releases - set(by_release)
    if missing:
        raise SystemExit(
            "retained release snapshots are missing: " + ", ".join(sorted(missing))
        )

    forget_ids: list[str] = []
    for release_id, release_snapshots in by_release.items():
        ordered = sorted(
            release_snapshots,
            key=lambda snapshot: datetime.fromisoformat(str(snapshot["time"]).replace("Z", "+00:00")),
            reverse=True,
        )
        if release_id in retained_releases:
            forget_ids.extend(str(snapshot["id"]) for snapshot in ordered[1:])
        else:
            forget_ids.extend(str(snapshot["id"]) for snapshot in ordered)
    return forget_ids


def main() -> int:
    arguments = parse_arguments()
    validate_arguments(arguments)
    if not os.environ.get("RESTIC_REPOSITORY") or not os.environ.get("RESTIC_PASSWORD_FILE"):
        raise SystemExit("RESTIC_REPOSITORY and RESTIC_PASSWORD_FILE are required")

    snapshots = load_snapshots()
    forget_ids = release_forget_ids(snapshots, set(arguments.retain_release)) \
        if arguments.retain_release else []

    report = {
        "mode": "apply" if arguments.apply else "dry-run",
        "scheduled_policy": {
            "keep_daily": arguments.keep_daily,
            "keep_weekly": arguments.keep_weekly,
        },
        "retained_releases": arguments.retain_release,
        "release_snapshots_to_forget": forget_ids,
        "prune": arguments.prune,
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    if not arguments.apply:
        return 0

    restic_command(
        "forget",
        "--tag",
        "scheduled",
        "--keep-daily",
        str(arguments.keep_daily),
        "--keep-weekly",
        str(arguments.keep_weekly),
        "--keep-tag",
        "release-point",
    )
    if forget_ids:
        restic_command("forget", *forget_ids)
    if arguments.prune:
        restic_command("prune")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        print(f"restic command failed with exit status {error.returncode}", file=sys.stderr)
        raise SystemExit(error.returncode) from error
