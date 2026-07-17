#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
state_dir="${BACKUP_STATE_DIR:-/var/lib/utility-watershed-analytics/backup}"
output_dir="${BACKUP_OUTPUT_DIR:-/var/lib/utility-watershed-analytics/backup/staging}"

for command in awk date dirname install mktemp mv rm; do
    command -v "$command" >/dev/null 2>&1 \
        || { printf 'ERROR: Required command not found: %s\n' "$command" >&2; exit 1; }
done

install -d -m 700 -- "$state_dir" "$output_dir"
runtime_dir="$(mktemp -d "${XDG_RUNTIME_DIR:-/tmp}/uwa-scheduled-backup.XXXXXX")"
cleanup() {
    rm -rf -- "$runtime_dir"
}
trap cleanup EXIT

local_result="$runtime_dir/local-result"
publish_result="$runtime_dir/publish-result"

BACKUP_RESULT_FILE="$local_result" \
    "$script_dir/backup_database.sh" --output-dir "$output_dir"

if [[ "${BACKUP_FORCE_FAILURE:-}" == "after-local-backup" ]]; then
    printf 'ERROR: Forced failure after local backup\n' >&2
    exit 97
fi

backup_set="$(awk -F= '$1 == "backup_set" {print substr($0, index($0, "=") + 1)}' "$local_result")"
[[ -n "$backup_set" ]] || { printf 'ERROR: Local backup did not report a backup set\n' >&2; exit 1; }

publish_arguments=(--backup-set "$backup_set")
if [[ -n "${BACKUP_RELEASE_ID:-}" ]]; then
    publish_arguments+=(--release-id "$BACKUP_RELEASE_ID")
fi
BACKUP_PUBLISH_RESULT_FILE="$publish_result" \
    "$script_dir/publish_backup.sh" "${publish_arguments[@]}"

snapshot_id="$(awk -F= '$1 == "snapshot_id" {print substr($0, index($0, "=") + 1)}' "$publish_result")"
published_utc="$(awk -F= '$1 == "published_utc" {print substr($0, index($0, "=") + 1)}' "$publish_result")"
[[ -n "$snapshot_id" && -n "$published_utc" ]] \
    || { printf 'ERROR: Publication result is incomplete\n' >&2; exit 1; }

state_partial="$(mktemp "$state_dir/.last-success.XXXXXX")"
{
    printf 'published_utc=%s\n' "$published_utc"
    printf 'snapshot_id=%s\n' "$snapshot_id"
    printf 'backup_set_name=%s\n' "$(basename "$backup_set")"
} >"$state_partial"
mv -- "$state_partial" "$state_dir/last-success"

trap - EXIT
cleanup
printf 'Scheduled encrypted backup completed: snapshot_id=%s\n' "$snapshot_id"
