#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
retained_release_ids="${BACKUP_RETAIN_RELEASE_IDS:-}"

[[ -n "$retained_release_ids" ]] || {
    printf 'ERROR: BACKUP_RETAIN_RELEASE_IDS is required\n' >&2
    exit 1
}

IFS=',' read -r -a releases <<<"$retained_release_ids"
retention_arguments=(--apply --prune)
for release_id in "${releases[@]}"; do
    [[ -n "$release_id" && "$release_id" == "${release_id//[[:space:]]/}" ]] || {
        printf 'ERROR: Retained release IDs must be non-empty and contain no whitespace\n' >&2
        exit 1
    }
    retention_arguments+=(--retain-release "$release_id")
done

exec "$script_dir/backup_retention.py" "${retention_arguments[@]}"
