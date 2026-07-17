#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

restic_bin="${RESTIC_BIN:-restic}"
maximum_age_seconds="${BACKUP_MAX_AGE_SECONDS:-90000}"

usage() {
    cat <<EOF
Usage: $(basename "$0")

Fail when the newest encrypted database snapshot is older than
BACKUP_MAX_AGE_SECONDS (default: 90000, allowing the 24-hour RPO plus 1 hour
of scheduler and notification tolerance).
EOF
}

if (($# > 0)); then
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'ERROR: Unknown option: %s\n' "$1" >&2
            exit 1
            ;;
    esac
fi

[[ "$maximum_age_seconds" =~ ^[1-9][0-9]*$ ]] \
    || { printf 'ERROR: BACKUP_MAX_AGE_SECONDS must be positive\n' >&2; exit 1; }
[[ -n "${RESTIC_REPOSITORY:-}" ]] \
    || { printf 'ERROR: RESTIC_REPOSITORY is required\n' >&2; exit 1; }
[[ -n "${RESTIC_PASSWORD_FILE:-}" && -r "$RESTIC_PASSWORD_FILE" ]] \
    || { printf 'ERROR: RESTIC_PASSWORD_FILE is required and readable\n' >&2; exit 1; }
[[ -x "$restic_bin" ]] \
    || { printf 'ERROR: Restic executable is unavailable: %s\n' "$restic_bin" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 \
    || { printf 'ERROR: python3 is required\n' >&2; exit 1; }
for command in mktemp rm; do
    command -v "$command" >/dev/null 2>&1 \
        || { printf 'ERROR: Required command not found: %s\n' "$command" >&2; exit 1; }
done

snapshots_file="$(mktemp /tmp/uwa-backup-snapshots.XXXXXX)"
cleanup() {
    rm -- "$snapshots_file"
}
trap cleanup EXIT
"$restic_bin" snapshots --json --tag uwa-database >"$snapshots_file" \
    || { printf 'ERROR: Could not query the encrypted backup repository\n' >&2; exit 1; }

python3 - "$maximum_age_seconds" "$snapshots_file" <<'PY'
import datetime as dt
import json
import sys

maximum_age = int(sys.argv[1])
with open(sys.argv[2], encoding="utf-8") as snapshot_stream:
    snapshots = json.load(snapshot_stream)
if not snapshots:
    raise SystemExit("ERROR: No encrypted database snapshots exist")

newest_snapshot = max(
    snapshots,
    key=lambda snapshot: dt.datetime.fromisoformat(snapshot["time"].replace("Z", "+00:00")),
)
snapshot_time = dt.datetime.fromisoformat(newest_snapshot["time"].replace("Z", "+00:00"))
now = dt.datetime.now(dt.timezone.utc)
age = int((now - snapshot_time).total_seconds())
if age < 0:
    raise SystemExit("ERROR: Newest snapshot timestamp is in the future")
if age > maximum_age:
    raise SystemExit(
        f"ERROR: Newest encrypted database snapshot is stale: age_seconds={age} "
        f"maximum={maximum_age}"
    )
print(f"Backup freshness passed: age_seconds={age} maximum={maximum_age}")
PY

trap - EXIT
cleanup
