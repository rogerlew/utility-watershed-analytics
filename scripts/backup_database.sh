#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly DEFAULT_CONTAINER="postgis"
readonly DEFAULT_OUTPUT_DIR="/workdir/backups/utility-watershed-analytics"
readonly DEFAULT_SPACE_MARGIN_BYTES=$((5 * 1024 * 1024 * 1024))
readonly DEFAULT_LOCK_WAIT_TIMEOUT="60s"

container="${POSTGRES_CONTAINER:-$DEFAULT_CONTAINER}"
output_dir="${BACKUP_OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}"
space_margin_bytes="${BACKUP_SPACE_MARGIN_BYTES:-$DEFAULT_SPACE_MARGIN_BYTES}"
lock_wait_timeout="${BACKUP_LOCK_WAIT_TIMEOUT:-$DEFAULT_LOCK_WAIT_TIMEOUT}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Create and verify a custom-format backup of the PostgreSQL database running
in the production PostGIS container. The archive is streamed directly to the
host, so it is not stored in the container or its anonymous data volume.

Options:
  --container NAME    PostgreSQL container name (default: $DEFAULT_CONTAINER)
  --output-dir PATH   Host backup directory (default: $DEFAULT_OUTPUT_DIR)
  -h, --help          Show this help

Environment overrides:
  POSTGRES_CONTAINER          Same as --container
  BACKUP_OUTPUT_DIR           Same as --output-dir
  BACKUP_SPACE_MARGIN_BYTES   Free-space margin beyond pg_database_size
  BACKUP_LOCK_WAIT_TIMEOUT    Maximum wait for a pg_dump table lock (default: 60s)
  BACKUP_LOCK_FILE            Host-wide advisory lock file

The script never deletes previous backups.
The globals file can contain role password verifiers; treat every artifact as sensitive.
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
        --container)
            (($# >= 2)) || die "--container requires a value"
            container="$2"
            shift 2
            ;;
        --output-dir)
            (($# >= 2)) || die "--output-dir requires a value"
            output_dir="$2"
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

for command in awk basename date df docker flock grep hostname id install \
    mv sha256sum sync tee tr wc; do
    command -v "$command" >/dev/null 2>&1 || die "Required command not found: $command"
done

[[ "$space_margin_bytes" =~ ^[0-9]+$ ]] \
    || die "BACKUP_SPACE_MARGIN_BYTES must be a non-negative integer"
[[ "$lock_wait_timeout" =~ ^[0-9]+(ms|s|min|h)?$ ]] \
    || die "BACKUP_LOCK_WAIT_TIMEOUT must be a PostgreSQL duration such as 60s"

runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
[[ -d "$runtime_dir" && -w "$runtime_dir" ]] \
    || die "User runtime directory is unavailable: $runtime_dir"
lock_file="${BACKUP_LOCK_FILE:-$runtime_dir/utility-watershed-analytics-db-backup.lock}"
exec 9>"$lock_file"
flock -n 9 || die "Another database backup is already running (lock: $lock_file)"

if [[ ! -d "$output_dir" ]]; then
    install -d -m 700 -- "$output_dir"
fi
[[ -w "$output_dir" ]] || die "Backup directory is not writable: $output_dir"

timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
log_file="$output_dir/database-backup-$timestamp.log"
exec > >(tee -a "$log_file") 2>&1

docker inspect "$container" >/dev/null 2>&1 \
    || die "PostgreSQL container not found: $container"
[[ "$(docker inspect --format '{{.State.Running}}' "$container")" == "true" ]] \
    || die "PostgreSQL container is not running: $container"

docker exec "$container" sh -ceu '
    command -v pg_dump >/dev/null
    command -v pg_dumpall >/dev/null
    command -v pg_restore >/dev/null
    pg_isready -q --username "${POSTGRES_USER:?}" --dbname "${POSTGRES_DB:?}"
' || die "PostgreSQL backup tools or database readiness check failed"

database_name="$(
    docker exec "$container" sh -ceu 'printf "%s" "${POSTGRES_DB:?}"'
)"
database_user="$(
    docker exec "$container" sh -ceu 'printf "%s" "${POSTGRES_USER:?}"'
)"
[[ -n "$database_name" ]] || die "POSTGRES_DB is empty in container $container"
[[ -n "$database_user" ]] || die "POSTGRES_USER is empty in container $container"

safe_database_name="${database_name//[^a-zA-Z0-9_.-]/_}"
backup_base="${safe_database_name}_${timestamp}"
archive="$output_dir/$backup_base.dump"
archive_partial="$archive.partial"
globals_file="$output_dir/$backup_base.globals.sql"
globals_partial="$globals_file.partial"
checksum_file="$archive.sha256"
checksum_partial="$checksum_file.partial"
toc_file="$archive.toc.txt"
toc_partial="$toc_file.partial"
metadata_file="$archive.metadata.txt"
metadata_partial="$metadata_file.partial"
complete_file="$archive.complete"
complete_partial="$complete_file.partial"

for path in \
    "$archive" "$archive_partial" \
    "$globals_file" "$globals_partial" \
    "$checksum_file" "$checksum_partial" \
    "$toc_file" "$toc_partial" \
    "$metadata_file" "$metadata_partial" \
    "$complete_file" "$complete_partial"; do
    [[ ! -e "$path" ]] || die "Refusing to overwrite existing path: $path"
done

completed=0
on_exit() {
    local status=$?
    if ((status != 0 || completed == 0)); then
        log ERROR "Backup did not complete successfully (exit status $status)"
        if [[ -e "$archive_partial" ]]; then
            log ERROR "Incomplete archive retained for diagnosis: $archive_partial"
        elif [[ -e "$archive" && ! -e "$complete_file" ]]; then
            log ERROR "Archive exists without a completion marker; do not trust it yet: $archive"
        fi
    fi
}
trap on_exit EXIT

read_only_psql() {
    local sql="$1"
    docker exec "$container" sh -ceu '
        export PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=15000"
        exec psql -X -qAt --no-password -v ON_ERROR_STOP=1 \
            --username "${POSTGRES_USER:?}" \
            --dbname "${POSTGRES_DB:?}" \
            --command "$1"
    ' sh "$sql"
}

database_size_bytes="$(read_only_psql 'SELECT pg_database_size(current_database());')"
[[ "$database_size_bytes" =~ ^[0-9]+$ ]] \
    || die "Could not determine database size"

available_bytes="$(df -PB1 -- "$output_dir" | awk 'NR == 2 {print $4}')"
[[ "$available_bytes" =~ ^[0-9]+$ ]] \
    || die "Could not determine free space for $output_dir"

required_bytes=$((database_size_bytes + space_margin_bytes))
if ((available_bytes < required_bytes)); then
    die "Insufficient free space: available=$available_bytes required=$required_bytes"
fi

server_version="$(read_only_psql 'SHOW server_version;')"
postgis_version="$(read_only_psql "SELECT extversion FROM pg_extension WHERE extname = 'postgis';")"
container_image="$(docker inspect --format '{{.Config.Image}}' "$container")"
container_image_id="$(docker inspect --format '{{.Image}}' "$container")"
started_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

log INFO "Starting PostgreSQL backup"
log INFO "Container: $container"
log INFO "Database: $database_name"
log INFO "Output archive: $archive"
log INFO "Database size: $database_size_bytes bytes"
log INFO "Available space: $available_bytes bytes"

dump_started_seconds=$SECONDS
if ! docker exec -e BACKUP_LOCK_WAIT_TIMEOUT="$lock_wait_timeout" "$container" sh -ceu '
    export PGOPTIONS="-c default_transaction_read_only=on"
    exec pg_dump \
        --host /var/run/postgresql \
        --username "${POSTGRES_USER:?}" \
        --dbname "${POSTGRES_DB:?}" \
        --format custom \
        --compress 6 \
        --lock-wait-timeout "$BACKUP_LOCK_WAIT_TIMEOUT" \
        --verbose \
        --no-password
' >"$archive_partial"; then
    die "pg_dump failed; the partial archive is not a valid backup"
fi
dump_duration_seconds=$((SECONDS - dump_started_seconds))

[[ -s "$archive_partial" ]] || die "pg_dump produced an empty archive"

log INFO "Capturing cluster-global roles, memberships, grants, and tablespaces"
if ! docker exec "$container" sh -ceu '
    export PGOPTIONS="-c default_transaction_read_only=on"
    exec pg_dumpall \
        --host /var/run/postgresql \
        --username "${POSTGRES_USER:?}" \
        --database "${POSTGRES_DB:?}" \
        --globals-only \
        --no-password
' >"$globals_partial"; then
    die "pg_dumpall --globals-only failed"
fi
[[ -s "$globals_partial" ]] || die "pg_dumpall produced an empty globals file"

log INFO "Verifying archive structure with pg_restore --list"
docker exec -i "$container" pg_restore --list \
    <"$archive_partial" >"$toc_partial" \
    || die "pg_restore could not read the generated archive"

for required_table in \
    watershed_watershed \
    watershed_subcatchment \
    watershed_channel \
    django_migrations; do
    grep -Eq "TABLE DATA [^ ]+ ${required_table}( |$)" "$toc_partial" \
        || die "Verified archive is missing table data entry: $required_table"
done

log INFO "Fully decoding archive payload with pg_restore"
docker exec -i "$container" pg_restore --file /dev/null \
    <"$archive_partial" \
    || die "pg_restore could not fully decode the generated archive"

archive_size_bytes="$(wc -c <"$archive_partial" | tr -d '[:space:]')"
archive_sha256="$(sha256sum "$archive_partial" | awk '{print $1}')"
globals_size_bytes="$(wc -c <"$globals_partial" | tr -d '[:space:]')"
globals_sha256="$(sha256sum "$globals_partial" | awk '{print $1}')"
completed_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

{
    printf '%s  %s\n' "$archive_sha256" "$(basename "$archive")"
    printf '%s  %s\n' "$globals_sha256" "$(basename "$globals_file")"
} >"$checksum_partial"

{
    printf 'backup_started_utc=%s\n' "$started_at"
    printf 'backup_completed_utc=%s\n' "$completed_at"
    printf 'hostname=%s\n' "$(hostname -f 2>/dev/null || hostname)"
    printf 'container=%s\n' "$container"
    printf 'container_image=%s\n' "$container_image"
    printf 'container_image_id=%s\n' "$container_image_id"
    printf 'database=%s\n' "$database_name"
    printf 'database_user=%s\n' "$database_user"
    printf 'postgres_server_version=%s\n' "$server_version"
    printf 'postgis_version=%s\n' "$postgis_version"
    printf 'database_size_bytes_at_start=%s\n' "$database_size_bytes"
    printf 'archive_size_bytes=%s\n' "$archive_size_bytes"
    printf 'archive_sha256=%s\n' "$archive_sha256"
    printf 'globals_size_bytes=%s\n' "$globals_size_bytes"
    printf 'globals_sha256=%s\n' "$globals_sha256"
    printf 'dump_duration_seconds=%s\n' "$dump_duration_seconds"
    printf 'archive_validation=pg_restore_full_decode_to_dev_null\n'
    printf 'restore_tested=false\n'
} >"$metadata_partial"

log INFO "Synchronizing backup data to durable host storage"
sync -- \
    "$archive_partial" \
    "$globals_partial" \
    "$checksum_partial" \
    "$toc_partial" \
    "$metadata_partial"

mv -- "$globals_partial" "$globals_file"
mv -- "$checksum_partial" "$checksum_file"
mv -- "$toc_partial" "$toc_file"
mv -- "$metadata_partial" "$metadata_file"
mv -- "$archive_partial" "$archive"

sync -- \
    "$archive" \
    "$globals_file" \
    "$checksum_file" \
    "$toc_file" \
    "$metadata_file" \
    "$output_dir"

{
    printf 'completed_utc=%s\n' "$completed_at"
    printf 'archive=%s\n' "$(basename "$archive")"
    printf 'checksum=%s\n' "$(basename "$checksum_file")"
} >"$complete_partial"
sync -- "$complete_partial"
mv -- "$complete_partial" "$complete_file"
sync -- "$complete_file" "$output_dir"

completed=1
trap - EXIT

log INFO "Backup completed and verified"
log INFO "Archive size: $archive_size_bytes bytes"
log INFO "SHA-256: $archive_sha256"
log INFO "Duration: $dump_duration_seconds seconds"
log INFO "Archive: $archive"
log INFO "Globals: $globals_file"
log INFO "Checksum: $checksum_file"
log INFO "Metadata: $metadata_file"
log INFO "Table-of-contents: $toc_file"
log INFO "Completion marker: $complete_file"
log INFO "Verify checksums from $output_dir with: sha256sum --check $(basename "$checksum_file")"
