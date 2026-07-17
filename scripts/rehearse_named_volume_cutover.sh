#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
snapshot_id="${DB05_REHEARSAL_SNAPSHOT_ID:-}"
source_image="${DB05_REHEARSAL_POSTGIS_IMAGE:-}"
server_image="${RESTORE_SERVER_IMAGE:-}"
maximum_rto_seconds="${BACKUP_MAX_RTO_SECONDS:-}"
rehearsal_root="${DB05_REHEARSAL_ROOT:-}"
result_file="${DB05_REHEARSAL_RESULT_FILE:-}"
acknowledgement="${DB05_REHEARSAL_ACK:-}"

log() {
    printf '%s [%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2"
}

die() {
    log ERROR "$1" >&2
    exit 1
}

[[ "$(hostname -s)" == "forest1" ]] \
    || die "DB05 rehearsal may run only on forest1"
[[ "$acknowledgement" == "forest1-only" ]] \
    || die "DB05_REHEARSAL_ACK must be forest1-only"
[[ -n "$snapshot_id" && "$snapshot_id" =~ ^[0-9a-f]{64}$ ]] \
    || die "DB05_REHEARSAL_SNAPSHOT_ID must be an exact snapshot ID"
[[ "$source_image" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "DB05_REHEARSAL_POSTGIS_IMAGE must be an exact image ID"
[[ "$server_image" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "RESTORE_SERVER_IMAGE must be an exact image ID"
[[ "$maximum_rto_seconds" =~ ^[1-9][0-9]*$ ]] \
    || die "BACKUP_MAX_RTO_SECONDS must be a positive integer"
[[ "$rehearsal_root" == /wc1/utility-watershed-analytics-db-backups/rehearsals/* ]] \
    || die "DB05_REHEARSAL_ROOT must be below the protected rehearsal root"
[[ -n "$result_file" && "$result_file" == "$rehearsal_root"/* ]] \
    || die "DB05_REHEARSAL_RESULT_FILE must be below DB05_REHEARSAL_ROOT"
[[ -n "${RESTIC_REPOSITORY:-}" ]] \
    || die "RESTIC_REPOSITORY is required for the source snapshot"
[[ -n "${RESTIC_PASSWORD_FILE:-}" && -r "$RESTIC_PASSWORD_FILE" ]] \
    || die "RESTIC_PASSWORD_FILE is required and readable"

for command in awk chmod cmp date df dirname docker find grep hostname install \
    jq mktemp mv openssl restic rm seq sha256sum shred sleep tail tr; do
    command -v "$command" >/dev/null 2>&1 \
        || die "Required command not found: $command"
done
for helper in backup_database.sh database_inventory.sh publish_backup.sh \
    restore_database.sh run_restore_test.sh; do
    [[ -x "$script_dir/$helper" ]] || die "Required helper is unavailable: $helper"
done
docker image inspect "$source_image" >/dev/null 2>&1 \
    || die "Exact source PostGIS image is unavailable"
docker image inspect "$server_image" >/dev/null 2>&1 \
    || die "Exact server smoke image is unavailable"
docker image inspect caddy:2-alpine >/dev/null 2>&1 \
    || die "Pinned local maintenance image is unavailable"
docker image inspect alpine:3.22 >/dev/null 2>&1 \
    || die "Pinned local source-holder image is unavailable"
[[ ! -e "$rehearsal_root" ]] \
    || die "Rehearsal root already exists: $rehearsal_root"

available_root_bytes="$(df -PB1 /var/lib/docker | awk 'NR == 2 {print $4}')"
available_rehearsal_bytes="$(df -PB1 /wc1/utility-watershed-analytics-db-backups | awk 'NR == 2 {print $4}')"
minimum_root_bytes=$((120 * 1024 * 1024 * 1024))
minimum_rehearsal_bytes=$((20 * 1024 * 1024 * 1024))
((available_root_bytes >= minimum_root_bytes)) \
    || die "Insufficient Docker storage for rehearsal"
((available_rehearsal_bytes >= minimum_rehearsal_bytes)) \
    || die "Insufficient protected staging storage for rehearsal"

install -d -m 700 -- "$rehearsal_root"
work_dir="$(mktemp -d "$rehearsal_root/.work.XXXXXX")"
protected_dir="$rehearsal_root/protected"
evidence_dir="$rehearsal_root/evidence"
isolated_repository="$rehearsal_root/repository"
isolated_password="$protected_dir/restic-password"
install -d -m 700 -- "$protected_dir" "$evidence_dir"

suffix="$(date -u +'%Y%m%d%H%M%S')-$$"
prefix="uwa-db05-rehearsal-$suffix"
source_container="$prefix-source"
target_container="$prefix-target"
holder_container="$prefix-source-holder"
maintenance_container="$prefix-maintenance"
source_network="$prefix-source-net"
target_network="$prefix-target-net"
maintenance_network="$prefix-maintenance-net"
target_volume="$prefix-postgres-data"
source_volume=""
source_database=""
source_user=""
target_user=""
completed=0

cleanup() {
    local cleanup_status=$?
    set +e
    for container in "$maintenance_container" "$target_container" \
        "$source_container" "$holder_container"; do
        docker container rm --force --volumes "$container" >/dev/null 2>&1
    done
    for network in "$maintenance_network" "$target_network" "$source_network"; do
        docker network rm "$network" >/dev/null 2>&1
    done
    if [[ -n "$target_volume" ]]; then
        docker volume rm "$target_volume" >/dev/null 2>&1
    fi
    if [[ -n "$source_volume" ]]; then
        docker volume rm "$source_volume" >/dev/null 2>&1
    fi
    find "$work_dir" -type f -exec shred --remove --zero {} + >/dev/null 2>&1
    rm -rf -- "$work_dir"
    if ((cleanup_status != 0 || completed == 0)); then
        log ERROR "Rehearsal failed; disposable resources were cleaned"
        log ERROR "Protected encrypted evidence root retained: $rehearsal_root"
    fi
    return "$cleanup_status"
}
trap cleanup EXIT

wait_for_postgres() {
    local container="$1"
    local user="$2"
    for attempt in $(seq 1 90); do
        if docker exec "$container" pg_isready --quiet \
            --username "$user" --dbname postgres; then
            return 0
        fi
        sleep 1
    done
    return 1
}

run_smoke() {
    local network="$1"
    local environment_file="$2"
    local output_file="$3"
    docker run --rm \
        --network "$network" \
        --env-file "$environment_file" \
        "$server_image" \
        python manage.py restore_smoke >"$output_file"
    tail -n 1 "$output_file" \
        | jq -e '.database_connectivity == "passed" and .watershed_count > 0' \
            >/dev/null
}

active_writer_count() {
    local container="$1"
    local user="$2"
    local database="$3"
    docker exec "$container" psql -X -qAt --no-password \
        --username "$user" --dbname "$database" \
        --set ON_ERROR_STOP=1 \
        --command "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state <> 'idle';"
}

capture_inventory() {
    local container="$1"
    local user="$2"
    local database="$3"
    local output="$4"
    "$script_dir/database_inventory.sh" \
        --container "$container" \
        --database "$database" \
        --user "$user" \
        --output-dir "$output" >/dev/null
}

compare_inventory() {
    local first="$1"
    local second="$2"
    for name in extensions.tsv migrations.tsv sequences.tsv \
        table-fingerprints.tsv; do
        cmp --silent "$first/$name" "$second/$name" \
            || die "Database inventory drifted during quiescence: $name"
    done
}

create_postgres_environment() {
    local path="$1"
    local user="$2"
    local password="$3"
    local bootstrap_database="$4"
    {
        printf 'POSTGRES_USER=%s\n' "$user"
        printf 'POSTGRES_PASSWORD=%s\n' "$password"
        printf 'POSTGRES_DB=%s\n' "$bootstrap_database"
    } >"$path"
    chmod 600 "$path"
}

create_application_environment() {
    local path="$1"
    local user="$2"
    local password="$3"
    local database="$4"
    {
        printf 'POSTGRES_USER=%s\n' "$user"
        printf 'POSTGRES_PW=%s\n' "$password"
        printf 'POSTGRES_DB=%s\n' "$database"
        printf 'DJANGO_SECRET_KEY=%s\n' "$(openssl rand -base64 48 | tr -d '\n')"
        printf 'DEBUG=False\n'
        printf 'APP_ENVIRONMENT=production\n'
    } >"$path"
    chmod 600 "$path"
}

backup_container() {
    local container="$1"
    local database="$2"
    local user="$3"
    local output_dir="$4"
    local backup_result="$5"
    POSTGRES_CONTAINER="$container" \
    BACKUP_DATABASE_NAME="$database" \
    BACKUP_DATABASE_USER="$user" \
    BACKUP_OUTPUT_DIR="$output_dir" \
    BACKUP_RESULT_FILE="$backup_result" \
    BACKUP_LOCK_FILE="$work_dir/backup.lock" \
        "$script_dir/backup_database.sh"
}

publish_to_isolated_repository() {
    local backup_set="$1"
    local release_id="$2"
    local publish_result="$3"
    RESTIC_REPOSITORY="$isolated_repository" \
    RESTIC_PASSWORD_FILE="$isolated_password" \
    BACKUP_RESTIC_READ_DATA_SUBSET="5%" \
    BACKUP_PUBLISH_RESULT_FILE="$publish_result" \
        "$script_dir/publish_backup.sh" \
        --backup-set "$backup_set" \
        --release-id "$release_id"
}

started_epoch="$(date +%s)"
log INFO "Restoring exact encrypted source snapshot into protected staging"
snapshot_json="$work_dir/source-snapshot.json"
restic snapshots --json "$snapshot_id" >"$snapshot_json"
[[ "$(jq -r 'length' "$snapshot_json")" == "1" ]] \
    || die "Exact source snapshot was not uniquely resolved"
[[ "$(jq -r '.[0].id' "$snapshot_json")" == "$snapshot_id" ]] \
    || die "Resolved source snapshot ID differs"
source_path="$(jq -r '.[0].paths | if length == 1 then .[0] else empty end' "$snapshot_json")"
[[ "$source_path" == /* && "$source_path" != *".."* ]] \
    || die "Source snapshot path is not absolute and normalized"
restored_root="$work_dir/source-restored"
install -d -m 700 -- "$restored_root"
restic restore "$snapshot_id" --target "$restored_root" >/dev/null
source_backup_set="$restored_root$source_path"
[[ -d "$source_backup_set" ]] || die "Source backup set is absent after restore"
(
    cd -- "$source_backup_set"
    sha256sum --check checksums.sha256 >/dev/null
) || die "Source backup checksums failed"
source_database="$(awk -F= '$1 == "database" {print substr($0, index($0, "=") + 1)}' "$source_backup_set/metadata.txt")"
metadata_image="$(awk -F= '$1 == "container_image_id" {print substr($0, index($0, "=") + 1)}' "$source_backup_set/metadata.txt")"
[[ -n "$source_database" ]] || die "Source database metadata is absent"
[[ "$metadata_image" == "$source_image" ]] || die "Source image differs from frozen image"

log INFO "Initializing isolated encrypted rehearsal repository"
openssl rand -base64 48 | tr -d '\n' >"$isolated_password"
chmod 600 "$isolated_password"
RESTIC_REPOSITORY="$isolated_repository" \
RESTIC_PASSWORD_FILE="$isolated_password" \
    restic init >/dev/null

source_password="$(openssl rand -base64 48 | tr -d '\n')"
target_password="$(openssl rand -base64 48 | tr -d '\n')"
source_user="uwa_db05_source_${RANDOM}_$$"
target_user="uwa_db05_target_${RANDOM}_$$"
source_postgres_env="$work_dir/source-postgres.env"
target_postgres_env="$work_dir/target-postgres.env"
source_application_env="$work_dir/source-application.env"
target_application_env="$work_dir/target-application.env"
create_postgres_environment \
    "$source_postgres_env" "$source_user" "$source_password" "${source_user}_bootstrap"
create_postgres_environment \
    "$target_postgres_env" "$target_user" "$target_password" "${target_user}_bootstrap"
create_application_environment \
    "$source_application_env" "$source_user" "$source_password" "$source_database"
create_application_environment \
    "$target_application_env" "$target_user" "$target_password" "$source_database"

docker network create --internal "$source_network" >/dev/null
docker network create --internal "$target_network" >/dev/null
docker network create --internal "$maintenance_network" >/dev/null

maintenance_config="$work_dir/Caddyfile.maintenance"
printf ':8080 {\n    respond "maintenance" 503\n}\n' >"$maintenance_config"
docker run --detach \
    --name "$maintenance_container" \
    --network "$maintenance_network" \
    --network-alias maintenance \
    --label com.utility-watershed-analytics.db05-rehearsal=true \
    --mount "type=bind,source=$maintenance_config,destination=/etc/caddy/Caddyfile,readonly" \
    caddy:2-alpine >/dev/null
sleep 1
maintenance_probe="$(docker exec "$maintenance_container" wget -S -O /dev/null http://127.0.0.1:8080/ 2>&1 || true)"
grep -q '503' <<<"$maintenance_probe" || die "Maintenance response did not return 503"

log INFO "Creating production-shaped anonymous source"
docker run --detach \
    --name "$source_container" \
    --network "$source_network" \
    --network-alias db \
    --label com.utility-watershed-analytics.restore-target=true \
    --label com.utility-watershed-analytics.db05-rehearsal=true \
    --env-file "$source_postgres_env" \
    "$source_image" >/dev/null
wait_for_postgres "$source_container" "$source_user" \
    || die "Anonymous source did not become ready"
source_volume="$(docker inspect "$source_container" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')"
[[ "$source_volume" =~ ^[0-9a-f]{64}$ ]] \
    || die "Source did not receive an anonymous Docker volume"
[[ -z "$(docker port "$source_container")" ]] \
    || die "Source unexpectedly publishes a host port"
RESTORE_RESULT_FILE="$evidence_dir/source-restore-result" \
    "$script_dir/restore_database.sh" \
    --backup-set "$source_backup_set" \
    --target-container "$source_container"
run_smoke "$source_network" "$source_application_env" "$work_dir/source-smoke.json"

log INFO "Proving maintenance and bounded write quiescence"
[[ "$(active_writer_count "$source_container" "$source_user" "$source_database")" == "0" ]] \
    || die "Unexpected active source database writer"
capture_inventory \
    "$source_container" "$source_user" "$source_database" "$work_dir/quiescence-before"
sleep 5
[[ "$(active_writer_count "$source_container" "$source_user" "$source_database")" == "0" ]] \
    || die "Unexpected writer during quiescence interval"
capture_inventory \
    "$source_container" "$source_user" "$source_database" "$work_dir/quiescence-after"
compare_inventory "$work_dir/quiescence-before" "$work_dir/quiescence-after"

log INFO "Creating and encrypting pre-cutover logical backup"
pre_backup_result="$work_dir/pre-backup-result"
backup_container \
    "$source_container" "$source_database" "$source_user" \
    "$work_dir/pre-backup" "$pre_backup_result"
pre_backup_set="$(awk -F= '$1 == "backup_set" {print substr($0, index($0, "=") + 1)}' "$pre_backup_result")"
[[ -d "$pre_backup_set" ]] || die "Pre-cutover backup set is absent"
pre_publish_result="$evidence_dir/pre-publish-result"
publish_to_isolated_repository \
    "$pre_backup_set" "db05-rehearsal-pre-$suffix" "$pre_publish_result"
pre_snapshot_id="$(awk -F= '$1 == "snapshot_id" {print $2}' "$pre_publish_result")"
[[ "$pre_snapshot_id" =~ ^[0-9a-f]{64}$ ]] \
    || die "Pre-cutover encrypted snapshot ID is invalid"

log INFO "Stopping source and provisioning named target"
cutover_started_epoch="$(date +%s)"
docker stop --time 30 "$source_container" >/dev/null
docker volume create \
    --label com.utility-watershed-analytics.db05-rehearsal=true \
    --label com.utility-watershed-analytics.prune=prohibited \
    "$target_volume" >/dev/null
docker create \
    --name "$holder_container" \
    --label com.utility-watershed-analytics.db05-source-holder=true \
    --label com.utility-watershed-analytics.prune=prohibited \
    --mount "type=volume,source=$source_volume,destination=/held" \
    alpine:3.22 true >/dev/null
docker run --detach \
    --name "$target_container" \
    --network "$target_network" \
    --network-alias db \
    --label com.utility-watershed-analytics.restore-target=true \
    --label com.utility-watershed-analytics.db05-rehearsal=true \
    --env-file "$target_postgres_env" \
    --mount "type=volume,source=$target_volume,destination=/var/lib/postgresql/data" \
    "$source_image" >/dev/null
[[ -z "$(docker port "$target_container")" ]] \
    || die "Target unexpectedly publishes a host port"
wait_for_postgres "$target_container" "$target_user" \
    || die "Named target did not become ready"
RESTORE_RESULT_FILE="$evidence_dir/target-restore-result" \
    "$script_dir/restore_database.sh" \
    --backup-set "$pre_backup_set" \
    --target-container "$target_container"
run_smoke "$target_network" "$target_application_env" "$work_dir/target-smoke.json"
cutover_duration_seconds=$(($(date +%s) - cutover_started_epoch))
((cutover_duration_seconds <= maximum_rto_seconds)) \
    || die "Named-volume cutover exceeded maximum RTO"

log INFO "Exercising exact source rollback"
rollback_started_epoch="$(date +%s)"
docker stop --time 30 "$target_container" >/dev/null
docker start "$source_container" >/dev/null
wait_for_postgres "$source_container" "$source_user" \
    || die "Anonymous source did not restart for rollback"
run_smoke "$source_network" "$source_application_env" "$work_dir/rollback-smoke.json"
rollback_duration_seconds=$(($(date +%s) - rollback_started_epoch))
((rollback_duration_seconds <= maximum_rto_seconds)) \
    || die "Rollback exceeded maximum RTO"

log INFO "Reapplying accepted named target"
reapply_started_epoch="$(date +%s)"
docker stop --time 30 "$source_container" >/dev/null
docker start "$target_container" >/dev/null
wait_for_postgres "$target_container" "$target_user" \
    || die "Named target did not restart for reapply"
run_smoke "$target_network" "$target_application_env" "$work_dir/reapply-smoke.json"
reapply_duration_seconds=$(($(date +%s) - reapply_started_epoch))
((reapply_duration_seconds <= maximum_rto_seconds)) \
    || die "Target reapply exceeded maximum RTO"

log INFO "Proving named-volume restart and container-recreation persistence"
docker restart --time 30 "$target_container" >/dev/null
wait_for_postgres "$target_container" "$target_user" \
    || die "Named target failed container restart"
run_smoke "$target_network" "$target_application_env" "$work_dir/restart-smoke.json"
target_mount_before="$(docker inspect "$target_container" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')"
[[ "$target_mount_before" == "$target_volume" ]] \
    || die "Named target mount differs before recreation"
docker container rm --force "$target_container" >/dev/null
docker run --detach \
    --name "$target_container" \
    --network "$target_network" \
    --network-alias db \
    --label com.utility-watershed-analytics.restore-target=true \
    --label com.utility-watershed-analytics.db05-rehearsal=true \
    --env-file "$target_postgres_env" \
    --mount "type=volume,source=$target_volume,destination=/var/lib/postgresql/data" \
    "$source_image" >/dev/null
wait_for_postgres "$target_container" "$target_user" \
    || die "Recreated named target did not become ready"
target_mount_after="$(docker inspect "$target_container" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')"
[[ "$target_mount_after" == "$target_volume" ]] \
    || die "Named target mount differs after recreation"
run_smoke "$target_network" "$target_application_env" "$work_dir/recreate-smoke.json"

log INFO "Creating post-cutover backup and independent encrypted restore test"
post_backup_result="$work_dir/post-backup-result"
backup_container \
    "$target_container" "$source_database" "$target_user" \
    "$work_dir/post-backup" "$post_backup_result"
post_backup_set="$(awk -F= '$1 == "backup_set" {print substr($0, index($0, "=") + 1)}' "$post_backup_result")"
[[ -d "$post_backup_set" ]] || die "Post-cutover backup set is absent"
cmp --silent \
    "$pre_backup_set/inventory/table-fingerprints.tsv" \
    "$post_backup_set/inventory/table-fingerprints.tsv" \
    || die "Post-cutover table fingerprints differ from pre-cutover backup"
post_publish_result="$evidence_dir/post-publish-result"
publish_to_isolated_repository \
    "$post_backup_set" "db05-rehearsal-post-$suffix" "$post_publish_result"
post_snapshot_id="$(awk -F= '$1 == "snapshot_id" {print $2}' "$post_publish_result")"
[[ "$post_snapshot_id" =~ ^[0-9a-f]{64}$ ]] \
    || die "Post-cutover encrypted snapshot ID is invalid"
RESTIC_REPOSITORY="$isolated_repository" \
RESTIC_PASSWORD_FILE="$isolated_password" \
RESTORE_SERVER_IMAGE="$server_image" \
RESTORE_SERVER_SOURCE_DIR="" \
RESTORE_ALLOW_EMPTY_DATABASE=false \
BACKUP_MAX_RTO_SECONDS="$maximum_rto_seconds" \
RESTORE_TEST_RESULT_FILE="$evidence_dir/post-cutover-restore-test-result" \
    "$script_dir/run_restore_test.sh"

total_duration_seconds=$(($(date +%s) - started_epoch))
post_restore_snapshot="$(awk -F= '$1 == "snapshot_id" {print $2}' "$evidence_dir/post-cutover-restore-test-result")"
[[ "$post_restore_snapshot" == "$post_snapshot_id" ]] \
    || die "Post-cutover restore test selected an unexpected snapshot"
result_partial="$(mktemp "$evidence_dir/.db05-result.XXXXXX")"
{
    printf 'status=passed\n'
    printf 'source_snapshot_id=%s\n' "$snapshot_id"
    printf 'source_image_id=%s\n' "$source_image"
    printf 'source_database=%s\n' "$source_database"
    printf 'source_volume=%s\n' "$source_volume"
    printf 'source_volume_type=anonymous\n'
    printf 'source_holder=verified\n'
    printf 'target_volume=%s\n' "$target_volume"
    printf 'target_volume_type=named\n'
    printf 'pre_cutover_snapshot_id=%s\n' "$pre_snapshot_id"
    printf 'post_cutover_snapshot_id=%s\n' "$post_snapshot_id"
    printf 'maintenance_http_status=503\n'
    printf 'write_quiescence=passed\n'
    printf 'cutover_duration_seconds=%s\n' "$cutover_duration_seconds"
    printf 'rollback_duration_seconds=%s\n' "$rollback_duration_seconds"
    printf 'reapply_duration_seconds=%s\n' "$reapply_duration_seconds"
    printf 'maximum_rto_seconds=%s\n' "$maximum_rto_seconds"
    printf 'restart_persistence=passed\n'
    printf 'container_recreation_persistence=passed\n'
    printf 'pre_post_table_fingerprints=exact\n'
    printf 'post_cutover_restore_test=passed\n'
    printf 'total_duration_seconds=%s\n' "$total_duration_seconds"
    printf 'available_root_bytes_at_preflight=%s\n' "$available_root_bytes"
    printf 'available_rehearsal_bytes_at_preflight=%s\n' "$available_rehearsal_bytes"
} >"$result_partial"
mv -- "$result_partial" "$result_file"

restic_snapshot_summary="$evidence_dir/rehearsal-snapshots.tsv"
RESTIC_REPOSITORY="$isolated_repository" \
RESTIC_PASSWORD_FILE="$isolated_password" \
    restic snapshots --json \
    | jq -r '.[] | [.id, .time, .hostname, ((.tags // []) | join(","))] | @tsv' \
    >"$restic_snapshot_summary"

completed=1
log INFO "DB05 named-volume rehearsal passed"
log INFO "Cutover duration: $cutover_duration_seconds seconds"
log INFO "Rollback duration: $rollback_duration_seconds seconds"
log INFO "Reapply duration: $reapply_duration_seconds seconds"
log INFO "Protected encrypted rehearsal evidence: $rehearsal_root"
