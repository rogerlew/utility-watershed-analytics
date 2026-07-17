#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly DEFAULT_CONTAINER="postgis"
readonly DEFAULT_OUTPUT_DIR="/workdir/backups/utility-watershed-analytics"
readonly DEFAULT_SPACE_MARGIN_BYTES=$((5 * 1024 * 1024 * 1024))
readonly DEFAULT_LOCK_WAIT_TIMEOUT="60s"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
container="${POSTGRES_CONTAINER:-$DEFAULT_CONTAINER}"
output_dir="${BACKUP_OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}"
space_margin_bytes="${BACKUP_SPACE_MARGIN_BYTES:-$DEFAULT_SPACE_MARGIN_BYTES}"
lock_wait_timeout="${BACKUP_LOCK_WAIT_TIMEOUT:-$DEFAULT_LOCK_WAIT_TIMEOUT}"
result_file="${BACKUP_RESULT_FILE:-}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Create an atomic, verified custom-format backup set from the PostgreSQL
container. The archive is streamed to mode-0700 host staging and is never
stored in the container or its database volume.

Options:
  --container NAME    PostgreSQL container name (default: $DEFAULT_CONTAINER)
  --output-dir PATH   Host staging directory (default: $DEFAULT_OUTPUT_DIR)
  -h, --help          Show this help

Environment overrides:
  POSTGRES_CONTAINER          Same as --container
  BACKUP_OUTPUT_DIR           Same as --output-dir
  BACKUP_SPACE_MARGIN_BYTES   Free-space margin beyond pg_database_size
  BACKUP_LOCK_WAIT_TIMEOUT    Maximum wait for a pg_dump table lock (default: 60s)
  BACKUP_LOCK_FILE            Single-backup advisory lock file
  BACKUP_RESULT_FILE          Optional mode-0600 result file written atomically

The script never deletes previous backup sets. A completed set contains the
archive, globals, schema, secret-free comparison inventories, checksums,
metadata, and a completion marker. The globals file can contain role password
verifiers; treat the entire set as sensitive until encrypted off-host.
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

for command in awk basename date df dirname docker flock grep hostname id \
    install mktemp mv sha256sum sync tee tr wc; do
    command -v "$command" >/dev/null 2>&1 || die "Required command not found: $command"
done
[[ -x "$script_dir/database_inventory.sh" ]] \
    || die "Database inventory helper is not executable: $script_dir/database_inventory.sh"

[[ "$space_margin_bytes" =~ ^[0-9]+$ ]] \
    || die "BACKUP_SPACE_MARGIN_BYTES must be a non-negative integer"
[[ "$lock_wait_timeout" =~ ^[0-9]+(ms|s|min|h)?$ ]] \
    || die "BACKUP_LOCK_WAIT_TIMEOUT must be a PostgreSQL duration such as 60s"
[[ "$output_dir" != *$'\n'* ]] || die "Backup output path must not contain a newline"
[[ "$result_file" != *$'\n'* ]] || die "Backup result path must not contain a newline"

runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
[[ -d "$runtime_dir" && -w "$runtime_dir" ]] \
    || die "User runtime directory is unavailable: $runtime_dir"
lock_file="${BACKUP_LOCK_FILE:-$runtime_dir/utility-watershed-analytics-db-backup.lock}"
exec 9>"$lock_file"
flock -n 9 || die "Another database backup is already running (lock: $lock_file)"

docker inspect "$container" >/dev/null 2>&1 \
    || die "PostgreSQL container not found: $container"
[[ "$(docker inspect --format '{{.State.Running}}' "$container")" == "true" ]] \
    || die "PostgreSQL container is not running: $container"

docker exec "$container" sh -ceu '
    command -v pg_dump >/dev/null
    command -v pg_dumpall >/dev/null
    command -v pg_restore >/dev/null
    command -v psql >/dev/null
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

if [[ ! -d "$output_dir" ]]; then
    install -d -m 700 -- "$output_dir"
fi
[[ -w "$output_dir" ]] || die "Backup directory is not writable: $output_dir"

timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
safe_database_name="${database_name//[^a-zA-Z0-9_.-]/_}"
backup_set="$output_dir/${safe_database_name}_$timestamp"
[[ ! -e "$backup_set" ]] || die "Refusing to overwrite backup set: $backup_set"
install -d -m 700 -- "$backup_set"

log_file="$backup_set/backup.log"
exec > >(tee -a "$log_file") 2>&1

archive="$backup_set/database.dump"
archive_partial="$archive.partial"
globals_file="$backup_set/globals.sql"
globals_partial="$globals_file.partial"
schema_file="$backup_set/schema.sql"
schema_partial="$schema_file.partial"
toc_file="$backup_set/archive.toc.txt"
toc_partial="$toc_file.partial"
inventory_dir="$backup_set/inventory"
inventory_partial="$backup_set/inventory.partial"
metadata_file="$backup_set/metadata.txt"
metadata_partial="$metadata_file.partial"
checksum_file="$backup_set/checksums.sha256"
checksum_partial="$checksum_file.partial"
complete_file="$backup_set/complete"
complete_partial="$complete_file.partial"

completed=0
on_exit() {
    local status=$?
    if ((status != 0 || completed == 0)); then
        log ERROR "Backup did not complete successfully (exit status $status)"
        log ERROR "Incomplete backup set retained for diagnosis: $backup_set"
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
log INFO "Backup set: $backup_set"
log INFO "Database size: $database_size_bytes bytes"
log INFO "Available staging space: $available_bytes bytes"

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

log INFO "Capturing schema definition"
if ! docker exec "$container" sh -ceu '
    export PGOPTIONS="-c default_transaction_read_only=on"
    exec pg_dump \
        --host /var/run/postgresql \
        --username "${POSTGRES_USER:?}" \
        --dbname "${POSTGRES_DB:?}" \
        --schema-only \
        --no-password
' >"$schema_partial"; then
    die "pg_dump --schema-only failed"
fi
[[ -s "$schema_partial" ]] || die "pg_dump produced an empty schema file"

log INFO "Verifying archive structure with pg_restore --list"
docker exec -i "$container" pg_restore --list \
    <"$archive_partial" >"$toc_partial" \
    || die "pg_restore could not read the generated archive"

for required_table in watershed_watershed watershed_subcatchment \
    watershed_channel django_migrations; do
    grep -Eq "TABLE DATA [^ ]+ ${required_table}( |$)" "$toc_partial" \
        || die "Verified archive is missing table data entry: $required_table"
done

log INFO "Fully decoding archive payload with pg_restore"
docker exec -i "$container" pg_restore --file /dev/null \
    <"$archive_partial" \
    || die "pg_restore could not fully decode the generated archive"

log INFO "Capturing secret-free comparison inventory"
"$script_dir/database_inventory.sh" \
    --container "$container" \
    --database "$database_name" \
    --user "$database_user" \
    --output-dir "$inventory_partial"

archive_size_bytes="$(wc -c <"$archive_partial" | tr -d '[:space:]')"
archive_sha256="$(sha256sum "$archive_partial" | awk '{print $1}')"
globals_size_bytes="$(wc -c <"$globals_partial" | tr -d '[:space:]')"
globals_sha256="$(sha256sum "$globals_partial" | awk '{print $1}')"
schema_sha256="$(sha256sum "$schema_partial" | awk '{print $1}')"
completed_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

{
    printf 'backup_format_version=1\n'
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
    printf 'schema_sha256=%s\n' "$schema_sha256"
    printf 'dump_duration_seconds=%s\n' "$dump_duration_seconds"
    printf 'archive_validation=pg_restore_full_decode_to_dev_null\n'
    printf 'restore_tested=false\n'
} >"$metadata_partial"

checksum_entry() {
    local source_path="$1"
    local published_path="$2"
    printf '%s  %s\n' "$(sha256sum "$source_path" | awk '{print $1}')" "$published_path"
}

{
    checksum_entry "$archive_partial" database.dump
    checksum_entry "$globals_partial" globals.sql
    checksum_entry "$schema_partial" schema.sql
    checksum_entry "$toc_partial" archive.toc.txt
    checksum_entry "$metadata_partial" metadata.txt
    for inventory_path in "$inventory_partial"/*.tsv; do
        checksum_entry "$inventory_path" "inventory/$(basename "$inventory_path")"
    done
} >"$checksum_partial"

log INFO "Synchronizing backup set to local staging storage"
sync -- "$archive_partial" "$globals_partial" "$schema_partial" \
    "$toc_partial" "$metadata_partial" "$checksum_partial" \
    "$inventory_partial"/*.tsv

mv -- "$archive_partial" "$archive"
mv -- "$globals_partial" "$globals_file"
mv -- "$schema_partial" "$schema_file"
mv -- "$toc_partial" "$toc_file"
mv -- "$inventory_partial" "$inventory_dir"
mv -- "$metadata_partial" "$metadata_file"
mv -- "$checksum_partial" "$checksum_file"

sync -- "$archive" "$globals_file" "$schema_file" "$toc_file" \
    "$metadata_file" "$checksum_file" "$inventory_dir"/*.tsv "$backup_set"

{
    printf 'completed_utc=%s\n' "$completed_at"
    printf 'backup_set=%s\n' "$(basename "$backup_set")"
    printf 'checksum=checksums.sha256\n'
} >"$complete_partial"
sync -- "$complete_partial"
mv -- "$complete_partial" "$complete_file"
sync -- "$complete_file" "$backup_set" "$output_dir"

if [[ -n "$result_file" ]]; then
    result_parent="$(dirname -- "$result_file")"
    [[ -d "$result_parent" && -w "$result_parent" ]] \
        || die "Backup result directory is unavailable: $result_parent"
    result_partial="$(mktemp "$result_parent/.backup-result.XXXXXX")"
    {
        printf 'backup_set=%s\n' "$backup_set"
        printf 'metadata=%s\n' "$metadata_file"
        printf 'completion_marker=%s\n' "$complete_file"
    } >"$result_partial"
    mv -- "$result_partial" "$result_file"
fi

completed=1
trap - EXIT

log INFO "Backup completed and verified"
log INFO "Archive size: $archive_size_bytes bytes"
log INFO "SHA-256: $archive_sha256"
log INFO "Duration: $dump_duration_seconds seconds"
log INFO "Backup set: $backup_set"
log INFO "Checksum manifest: $checksum_file"
log INFO "Completion marker: $complete_file"
