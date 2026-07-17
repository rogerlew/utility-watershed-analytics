#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

failed_unit="${1:-unknown}"
webhook_file="${BACKUP_FAILURE_WEBHOOK_URL_FILE:-}"

for command in curl hostname logger mktemp python3 rm; do
    command -v "$command" >/dev/null 2>&1 \
        || { printf 'ERROR: Required command not found: %s\n' "$command" >&2; exit 1; }
done

message="Utility Watershed Analytics backup failure on $(hostname -f 2>/dev/null || hostname): $failed_unit"
logger --tag utility-watershed-analytics-backup -- "$message"

[[ -n "$webhook_file" && -r "$webhook_file" ]] || {
    printf 'ERROR: Backup failure logged locally, but no readable webhook credential is configured\n' >&2
    exit 1
}

webhook_url="$(<"$webhook_file")"
[[ "$webhook_url" == https://* ]] || {
    printf 'ERROR: Backup failure webhook must use HTTPS\n' >&2
    exit 1
}

payload_file="$(mktemp /tmp/uwa-backup-notification.XXXXXX)"
cleanup() {
    rm -f -- "$payload_file"
}
trap cleanup EXIT
python3 - "$message" >"$payload_file" <<'PY'
import json
import sys

json.dump({"text": sys.argv[1]}, sys.stdout)
PY

curl --fail --silent --show-error \
    --header 'Content-Type: application/json' \
    --data-binary "@$payload_file" \
    --output /dev/null \
    "$webhook_url"
