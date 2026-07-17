#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
restic_bin="${RESTIC_BIN:-restic}"
maximum_rto_seconds="${BACKUP_MAX_RTO_SECONDS:-}"
server_image="${RESTORE_SERVER_IMAGE:-}"
server_source_dir="${RESTORE_SERVER_SOURCE_DIR:-}"
result_file="${RESTORE_TEST_RESULT_FILE:-}"
allow_empty="${RESTORE_ALLOW_EMPTY_DATABASE:-false}"

usage() {
    cat <<EOF
Usage: $(basename "$0")

Restore the newest encrypted database snapshot into a disposable isolated
PostGIS container, compare the database inventory, and run the Django
restore_smoke command from RESTORE_SERVER_IMAGE.

Required environment:
  RESTIC_REPOSITORY
  RESTIC_PASSWORD_FILE
  BACKUP_MAX_RTO_SECONDS
  RESTORE_SERVER_IMAGE

Optional environment:
  RESTIC_BIN
  RESTORE_SERVER_SOURCE_DIR    Read-only source mount for a development image
  RESTORE_ALLOW_EMPTY_DATABASE=true
  RESTORE_TEST_RESULT_FILE     Atomic mode-0600 result file
EOF
}

log() {
    printf '%s [%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2"
}

die() {
    log ERROR "$1" >&2
    exit 1
}

if (($# > 0)); then
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
fi

[[ -n "${RESTIC_REPOSITORY:-}" ]] || die "RESTIC_REPOSITORY is required"
[[ -n "${RESTIC_PASSWORD_FILE:-}" && -r "$RESTIC_PASSWORD_FILE" ]] \
    || die "RESTIC_PASSWORD_FILE is required and readable"
[[ "$maximum_rto_seconds" =~ ^[1-9][0-9]*$ ]] \
    || die "BACKUP_MAX_RTO_SECONDS must be a positive integer"
[[ -n "$server_image" ]] || die "RESTORE_SERVER_IMAGE is required"
[[ "$server_image" =~ ^sha256:[0-9a-f]{64}$ \
    || "$server_image" =~ @sha256:[0-9a-f]{64}$ ]] \
    || die "RESTORE_SERVER_IMAGE must be an exact image ID or repository digest"
[[ "$allow_empty" == "true" || "$allow_empty" == "false" ]] \
    || die "RESTORE_ALLOW_EMPTY_DATABASE must be true or false"
[[ "$result_file" != *$'\n'* ]] || die "Restore-test result path must not contain a newline"

for command in awk basename chmod date dirname docker grep install mktemp mv \
    openssl python3 rm sed seq shred sleep tr; do
    command -v "$command" >/dev/null 2>&1 || die "Required command not found: $command"
done
[[ -x "$restic_bin" ]] || die "Restic executable is unavailable: $restic_bin"
[[ -x "$script_dir/restore_database.sh" ]] \
    || die "Restore helper is not executable: $script_dir/restore_database.sh"
docker image inspect "$server_image" >/dev/null 2>&1 \
    || die "Restore smoke server image is unavailable: $server_image"
if [[ -n "$server_source_dir" ]]; then
    [[ -d "$server_source_dir" ]] || die "RESTORE_SERVER_SOURCE_DIR is not a directory"
    server_source_dir="$(cd -- "$server_source_dir" && pwd)"
fi

runtime_dir="$(mktemp -d /tmp/uwa-restore-test.XXXXXX)"
restore_root="$runtime_dir/restored"
snapshot_file="$runtime_dir/snapshot.json"
postgres_env="$runtime_dir/postgres.env"
application_env="$runtime_dir/application.env"
database_result="$runtime_dir/database-result"
application_result="$runtime_dir/application-result.json"
target_suffix="$(date -u +'%Y%m%d%H%M%S')-$$"
target_container="uwa-restore-$target_suffix"
network_name="uwa-restore-$target_suffix"
container_created=0
network_created=0

cleanup() {
    local cleanup_status=$?
    set +e
    if ((container_created == 1)); then
        if ((cleanup_status != 0)); then
            log ERROR "Disposable restore target logs follow"
            docker logs --tail 100 "$target_container" >&2
        fi
        docker stop --time 5 "$target_container" >/dev/null 2>&1
        docker container rm --volumes "$target_container" >/dev/null 2>&1
    fi
    if ((network_created == 1)); then
        docker network rm "$network_name" >/dev/null 2>&1
    fi
    if [[ -f "$postgres_env" ]]; then
        shred --remove --zero "$postgres_env" >/dev/null 2>&1 || rm -- "$postgres_env"
    fi
    if [[ -f "$application_env" ]]; then
        shred --remove --zero "$application_env" >/dev/null 2>&1 || rm -- "$application_env"
    fi
    rm -rf -- "$runtime_dir"
    return "$cleanup_status"
}
trap cleanup EXIT

started_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
restore_started_seconds=$SECONDS

log INFO "Resolving newest encrypted database snapshot"
"$restic_bin" snapshots --json --tag uwa-database >"$snapshot_file" \
    || die "Could not query the encrypted backup repository"

mapfile -t snapshot_details < <(python3 - "$snapshot_file" <<'PY'
import json
import pathlib
import sys

with open(sys.argv[1], encoding="utf-8") as snapshot_stream:
    snapshots = json.load(snapshot_stream)
if not snapshots:
    raise SystemExit("no database snapshots are available")
snapshot = max(
    snapshots,
    key=lambda item: item["time"],
)
paths = snapshot.get("paths", [])
if len(paths) != 1:
    raise SystemExit("database snapshot must contain exactly one backup-set path")
source_path = pathlib.PurePosixPath(paths[0])
if not source_path.is_absolute() or ".." in source_path.parts:
    raise SystemExit("database snapshot path must be absolute and normalized")
print(snapshot["id"])
print(str(source_path))
PY
)
[[ "${#snapshot_details[@]}" == 2 ]] \
    || die "Could not identify the latest snapshot and backup-set path"
snapshot_id="${snapshot_details[0]}"
source_path="${snapshot_details[1]}"

install -d -m 700 -- "$restore_root"
log INFO "Restoring encrypted snapshot into disposable staging"
"$restic_bin" restore "$snapshot_id" --target "$restore_root" >/dev/null \
    || die "Encrypted snapshot restore failed"
restored_backup_set="$restore_root$source_path"
[[ -d "$restored_backup_set" ]] \
    || die "Restored snapshot does not contain the expected backup set"

metadata_value() {
    local key="$1"
    awk -F= -v key="$key" '$1 == key {print substr($0, index($0, "=") + 1); found=1} END {if (!found) exit 1}' \
        "$restored_backup_set/metadata.txt"
}

source_image_id="$(metadata_value container_image_id)" \
    || die "Restored metadata is missing the source image ID"
source_database="$(metadata_value database)" \
    || die "Restored metadata is missing the database name"
docker image inspect "$source_image_id" >/dev/null 2>&1 \
    || die "Exact source PostGIS image is unavailable locally: $source_image_id"

restore_user="uwa_restore_${RANDOM}_$$"
restore_password="$(openssl rand -base64 48 | tr -d '\n')"
restore_bootstrap_database="${restore_user}_bootstrap"
{
    printf 'POSTGRES_USER=%s\n' "$restore_user"
    printf 'POSTGRES_PASSWORD=%s\n' "$restore_password"
    printf 'POSTGRES_DB=%s\n' "$restore_bootstrap_database"
} >"$postgres_env"
{
    printf 'POSTGRES_USER=%s\n' "$restore_user"
    printf 'POSTGRES_PW=%s\n' "$restore_password"
    printf 'POSTGRES_DB=%s\n' "$source_database"
    printf 'DJANGO_SECRET_KEY=%s\n' "$(openssl rand -base64 48 | tr -d '\n')"
    printf 'DEBUG=False\n'
    printf 'APP_ENVIRONMENT=restore-test\n'
} >"$application_env"
chmod 600 "$postgres_env" "$application_env"

docker network create --internal "$network_name" >/dev/null
network_created=1
docker run --detach \
    --name "$target_container" \
    --network "$network_name" \
    --network-alias db \
    --label com.utility-watershed-analytics.restore-target=true \
    --env-file "$postgres_env" \
    "$source_image_id" >/dev/null
container_created=1

for attempt in $(seq 1 60); do
    if docker logs "$target_container" 2>&1 \
        | grep -q 'PostgreSQL init process complete; ready for start up.' \
        && docker exec "$target_container" pg_isready --quiet \
            --username "$restore_user" --dbname postgres; then
        break
    fi
    if [[ "$attempt" == 60 ]]; then
        die "Disposable restore target did not become ready"
    fi
    sleep 1
done

log INFO "Applying and comparing database backup"
RESTORE_RESULT_FILE="$database_result" \
    "$script_dir/restore_database.sh" \
    --backup-set "$restored_backup_set" \
    --target-container "$target_container"

server_arguments=(
    run
    --rm
    --network "$network_name"
    --env-file "$application_env"
)
if [[ -n "$server_source_dir" ]]; then
    server_arguments+=(--volume "$server_source_dir:/app/server:ro")
fi
server_arguments+=("$server_image" python manage.py restore_smoke)
if [[ "$allow_empty" == "true" ]]; then
    server_arguments+=(--allow-empty)
fi

log INFO "Running restored Django database and API smoke checks"
docker "${server_arguments[@]}" >"$application_result" \
    || die "Restored Django smoke checks failed"

restore_duration_seconds=$((SECONDS - restore_started_seconds))
if ((restore_duration_seconds > maximum_rto_seconds)); then
    die "Restore drill exceeded maximum RTO: achieved=$restore_duration_seconds maximum=$maximum_rto_seconds"
fi
completed_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

if [[ -n "$result_file" ]]; then
    result_parent="$(dirname -- "$result_file")"
    [[ -d "$result_parent" && -w "$result_parent" ]] \
        || die "Restore-test result directory is unavailable: $result_parent"
    result_partial="$(mktemp "$result_parent/.restore-test-result.XXXXXX")"
    {
        printf 'restore_started_utc=%s\n' "$started_at"
        printf 'restore_completed_utc=%s\n' "$completed_at"
        printf 'snapshot_id=%s\n' "$snapshot_id"
        printf 'restore_duration_seconds=%s\n' "$restore_duration_seconds"
        printf 'maximum_rto_seconds=%s\n' "$maximum_rto_seconds"
        printf 'database_comparison=passed\n'
        printf 'django_smoke=passed\n'
        sed -n '/^postgres_server_version=/p; /^postgis_version=/p; /^table_fingerprints=/p; /^schema=/p' \
            "$database_result"
        printf 'application_report=%s\n' "$(tr -d '\n' <"$application_result")"
    } >"$result_partial"
    mv -- "$result_partial" "$result_file"
fi

log INFO "Encrypted restore drill passed"
log INFO "Achieved RTO: $restore_duration_seconds seconds"
