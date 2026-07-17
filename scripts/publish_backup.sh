#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

backup_set=""
release_id="${BACKUP_RELEASE_ID:-}"
result_file="${BACKUP_PUBLISH_RESULT_FILE:-}"
restic_bin="${RESTIC_BIN:-restic}"
read_data_subset="${BACKUP_RESTIC_READ_DATA_SUBSET:-5%}"

usage() {
    cat <<EOF
Usage: $(basename "$0") --backup-set PATH [--release-id ID]

Publish one completed local backup set into an initialized encrypted restic
repository. RESTIC_REPOSITORY and RESTIC_PASSWORD_FILE must be supplied by the
protected runtime environment. S3-compatible repositories also use the normal
AWS credential environment supported by restic.

Environment:
  RESTIC_BIN                       Restic executable path
  BACKUP_RELEASE_ID                Optional active release identifier
  BACKUP_RESTIC_READ_DATA_SUBSET   Verification subset (default: 5%)
  BACKUP_PUBLISH_RESULT_FILE       Optional atomic mode-0600 result file
EOF
}

log() {
    printf '%s [%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2"
}

die() {
    log ERROR "$1" >&2
    exit 1
}

while (($# > 0)); do
    case "$1" in
        --backup-set)
            (($# >= 2)) || die "--backup-set requires a value"
            backup_set="$2"
            shift 2
            ;;
        --release-id)
            (($# >= 2)) || die "--release-id requires a value"
            release_id="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done

[[ -n "$backup_set" ]] || die "--backup-set is required"
[[ -n "${RESTIC_REPOSITORY:-}" ]] || die "RESTIC_REPOSITORY is required"
[[ -n "${RESTIC_PASSWORD_FILE:-}" ]] || die "RESTIC_PASSWORD_FILE is required"
[[ -r "$RESTIC_PASSWORD_FILE" ]] || die "RESTIC_PASSWORD_FILE is not readable"
[[ -x "$restic_bin" ]] || die "Restic executable is unavailable: $restic_bin"
[[ "$backup_set" != *$'\n'* ]] || die "Backup-set path must not contain a newline"
[[ "$result_file" != *$'\n'* ]] || die "Publish result path must not contain a newline"
[[ "$read_data_subset" =~ ^([1-9][0-9]?%|100%|[1-9][0-9]*/[1-9][0-9]*)$ ]] \
    || die "BACKUP_RESTIC_READ_DATA_SUBSET must be a percentage or N/M subset"
if [[ -n "$release_id" ]]; then
    [[ "$release_id" =~ ^[A-Za-z0-9][A-Za-z0-9._:-]*$ ]] \
        || die "Release ID contains unsupported tag characters"
fi

for command in awk date dirname hostname mktemp mv python3 realpath rm sha256sum; do
    command -v "$command" >/dev/null 2>&1 || die "Required command not found: $command"
done

backup_set="$(realpath -- "$backup_set")"
[[ -d "$backup_set" ]] || die "Backup set not found: $backup_set"
[[ -f "$backup_set/complete" ]] || die "Backup set lacks a completion marker"
(
    cd -- "$backup_set"
    sha256sum --check checksums.sha256 >/dev/null
) || die "Backup-set checksum verification failed before publication"

log INFO "Checking encrypted backup repository access"
"$restic_bin" snapshots --no-lock --json --latest 1 >/dev/null \
    || die "Restic repository is unavailable or not initialized"

temporary_dir="$(mktemp -d /tmp/uwa-restic-publish.XXXXXX)"
cleanup() {
    rm -rf -- "$temporary_dir"
}
trap cleanup EXIT
backup_report="$temporary_dir/backup.jsonl"

restic_arguments=(
    backup
    --json
    --host "$(hostname -f 2>/dev/null || hostname)"
    --tag uwa-database
    --tag scheduled
)
if [[ -n "$release_id" ]]; then
    restic_arguments+=(--tag release-point --tag "release:$release_id")
fi
restic_arguments+=(-- "$backup_set")

log INFO "Publishing encrypted backup set"
"$restic_bin" "${restic_arguments[@]}" >"$backup_report" \
    || die "Encrypted backup publication failed"

snapshot_id="$(python3 - "$backup_report" <<'PY'
import json
import sys

snapshot_id = ""
with open(sys.argv[1], encoding="utf-8") as report:
    for line in report:
        record = json.loads(line)
        if record.get("message_type") == "summary":
            snapshot_id = record.get("snapshot_id", "")
if not snapshot_id:
    raise SystemExit("restic backup report did not contain a snapshot ID")
print(snapshot_id)
PY
)" || die "Could not identify the published restic snapshot"

log INFO "Verifying repository metadata and rotating data subset"
"$restic_bin" check --read-data-subset "$read_data_subset" >/dev/null \
    || die "Restic repository verification failed after publication"

completed_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
if [[ -n "$result_file" ]]; then
    result_parent="$(dirname -- "$result_file")"
    [[ -d "$result_parent" && -w "$result_parent" ]] \
        || die "Publish result directory is unavailable: $result_parent"
    result_partial="$(mktemp "$result_parent/.publish-result.XXXXXX")"
    {
        printf 'published_utc=%s\n' "$completed_at"
        printf 'snapshot_id=%s\n' "$snapshot_id"
        printf 'backup_set_name=%s\n' "$(basename "$backup_set")"
        printf 'release_id=%s\n' "$release_id"
        printf 'repository_check=passed\n'
        printf 'read_data_subset=%s\n' "$read_data_subset"
    } >"$result_partial"
    mv -- "$result_partial" "$result_file"
fi

trap - EXIT
cleanup

log INFO "Encrypted backup published and verified"
log INFO "Snapshot ID: $snapshot_id"
