#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

expected_container_id="${DB05_EXPECTED_CONTAINER_ID:-}"
expected_image_id="${DB05_EXPECTED_IMAGE_ID:-}"
expected_source_volume="${DB05_EXPECTED_SOURCE_VOLUME:-}"
expected_caddy_image_id="${DB05_EXPECTED_CADDY_IMAGE_ID:-}"
expected_server_image_id="${DB05_EXPECTED_SERVER_IMAGE_ID:-}"
smoke_image_id="${DB05_SMOKE_IMAGE_ID:-}"
resume_after_target_restore="${DB05_RESUME_AFTER_TARGET_RESTORE:-false}"
task_root="${DB05_TASK_ROOT:-}"
acknowledgement="${DB05_PRODUCTION_ACK:-}"
maximum_rto_seconds="${BACKUP_MAX_RTO_SECONDS:-86400}"

project="utility-watershed-analytics"
project_network="utility-watershed-analytics_default"
target_volume="utility-watershed-analytics_postgres_data"
source_container="postgis"
source_rollback_container="uwa-db05-source-rollback"
source_holder="uwa-db05-source-holder"
target_temporary_container="uwa-db05-target-restore"
target_held_container="uwa-db05-target-held"
target_network="uwa-db05-target-net"
maintenance_container="uwa-db05-maintenance"
server_container="utility-watershed-analytics-server-1"
caddy_container="utility-watershed-analytics-caddy-1"
runtime_environment="/etc/utility-watershed-analytics/runtime.env"
database_identity="/etc/utility-watershed-analytics/database-identity"
canonical_compose="/workdir/utility-watershed-analytics/compose.prod.yml"
installed_backup_root="/home/roger/.local/lib/utility-watershed-analytics-backup/current"
backup_profile="/home/roger/.config/utility-watershed-analytics/backup.env"
bundle_root="/usr/local/lib/utility-watershed-analytics-runtime/db05-20260717-6f46aaf"

input_dir="$task_root/input"
evidence_dir="$task_root/evidence"
runtime_dir="$task_root/runtime"
compose_input="$input_dir/compose.prod.yml"
script_input="$input_dir/scripts"
unit_input="$input_dir/utility-watershed-analytics.service"
maintenance_gate="$task_root/maintenance-approved"
result_file="$evidence_dir/cutover-result"

log() {
    printf '%s [%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2"
}

die() {
    log ERROR "$1" >&2
    exit 1
}

write_state() {
    local state="$1"
    local partial
    partial="$(mktemp "$evidence_dir/.state.XXXXXX")"
    printf 'state=%s\nupdated_utc=%s\n' "$state" "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        >"$partial"
    mv -- "$partial" "$evidence_dir/state"
}

on_exit() {
    local status=$?
    if ((status != 0)); then
        write_state failed
        log ERROR "DB05 production harness stopped; maintenance and retained resources were preserved"
    fi
    return "$status"
}
trap on_exit EXIT

[[ "$(hostname -s)" == "wepp3" ]] || die "Production harness may run only on wepp3"
[[ "$(id -un)" == "roger" ]] || die "Production harness must run as roger"
[[ "$acknowledgement" == "wepp3-db05-production" ]] \
    || die "DB05_PRODUCTION_ACK must be wepp3-db05-production"
[[ "$expected_container_id" =~ ^[0-9a-f]{64}$ ]] \
    || die "Expected source container ID is invalid"
[[ "$expected_image_id" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "Expected source image ID is invalid"
[[ "$expected_source_volume" =~ ^[0-9a-f]{64}$ ]] \
    || die "Expected source volume ID is invalid"
[[ "$expected_caddy_image_id" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "Expected Caddy image ID is invalid"
[[ "$expected_server_image_id" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "Expected server image ID is invalid"
[[ "$smoke_image_id" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "Smoke image ID is invalid"
[[ "$resume_after_target_restore" == "true" || "$resume_after_target_restore" == "false" ]] \
    || die "DB05_RESUME_AFTER_TARGET_RESTORE must be true or false"
[[ "$task_root" == /var/lib/utility-watershed-analytics/db05-* ]] \
    || die "DB05_TASK_ROOT is outside the protected production task root"
[[ "$maximum_rto_seconds" =~ ^[1-9][0-9]*$ ]] \
    || die "BACKUP_MAX_RTO_SECONDS must be a positive integer"
[[ "${UWA_OPERATION_LOCK_MODE:-}" == "exclusive" && -n "${UWA_OPERATION_LOCK_FD:-}" ]] \
    || die "Production harness requires the inherited exclusive operations lock"

for command in awk cmp cp curl date df docker flock grep hostname install \
    mktemp mv openssl python3 sed seq sha256sum shred sleep stat sudo tail tee timeout tr; do
    command -v "$command" >/dev/null 2>&1 || die "Required command unavailable: $command"
done
for path in "$compose_input" "$unit_input" \
    "$script_input/backup_database.sh" \
    "$script_input/check_runtime_environment.sh" \
    "$script_input/database_identity.sh" \
    "$script_input/database_inventory.sh" \
    "$script_input/restore_database.sh" \
    "$script_input/start_runtime.sh" \
    "$script_input/with_operation_lock.sh"; do
    [[ -f "$path" && ! -L "$path" ]] || die "Required task input unavailable: $path"
done
sudo -n true || die "Passwordless sudo is unavailable"
[[ ! -e "$result_file" ]] || die "Production cutover result already exists"

capture_container_environment() {
    local container="$1"
    local name="$2"
    docker inspect "$container" --format '{{range .Config.Env}}{{println .}}{{end}}' \
        | awk -F= -v wanted="$name" '$1 == wanted {print substr($0, index($0, "=") + 1); exit}'
}

wait_for_database() {
    local container="$1"
    local user="$2"
    local database="$3"
    local attempt
    for attempt in $(seq 1 120); do
        if docker exec "$container" pg_isready --quiet \
            --username "$user" --dbname "$database"; then
            return 0
        fi
        sleep 1
    done
    return 1
}

run_smoke() {
    local network="$1"
    local output="$2"
    docker run --rm \
        --network "$network" \
        --env-file "$runtime_dir/application.env" \
        "$smoke_image_id" \
        python manage.py restore_smoke >"$output"
    tail -n 1 "$output" | python3 -c '
import json
import sys
report = json.load(sys.stdin)
if report.get("database_connectivity") != "passed" or report.get("watershed_count", 0) <= 0:
    raise SystemExit(1)
'
}

active_writer_count() {
    docker exec "$source_container" psql -X -qAt --no-password \
        --username "$production_user" --dbname "$production_database" \
        --set ON_ERROR_STOP=1 \
        --command "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND state<>'idle';"
}

capture_inventory() {
    local container="$1"
    local user="$2"
    local database="$3"
    local output="$4"
    "$script_input/database_inventory.sh" \
        --container "$container" \
        --database "$database" \
        --user "$user" \
        --output-dir "$output" >/dev/null
}

cutover_started_epoch="$(date +%s)"
write_state preflight

[[ "$(docker inspect "$source_container" --format '{{.Id}}')" == "$expected_container_id" ]] \
    || die "Source container identity changed"
[[ "$(docker inspect "$source_container" --format '{{.Image}}')" == "$expected_image_id" ]] \
    || die "Source image identity changed"
actual_source_volume="$(docker inspect "$source_container" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')"
[[ "$actual_source_volume" == "$expected_source_volume" ]] \
    || die "Source volume identity changed"
[[ "$(docker inspect "$source_container" --format '{{.State.Status}}')" == "running" ]] \
    || die "Source database is not running"
[[ "$(docker inspect "$source_container" --format '{{.State.Health.Status}}')" == "healthy" ]] \
    || die "Source database is not healthy"
[[ "$(docker inspect "$source_container" --format '{{.RestartCount}}')" == "0" ]] \
    || die "Source database restart count changed"
[[ "$(docker inspect "$caddy_container" --format '{{.Image}}')" == "$expected_caddy_image_id" ]] \
    || die "Caddy image identity changed"
[[ "$(docker inspect "$server_container" --format '{{.Image}}')" == "$expected_server_image_id" ]] \
    || die "Server image identity changed"
docker image inspect "$smoke_image_id" >/dev/null 2>&1 \
    || die "Exact smoke image is unavailable"
if [[ "$resume_after_target_restore" == "false" ]]; then
    for unexpected in "$source_rollback_container" "$source_holder" \
        "$target_temporary_container" "$target_held_container" "$maintenance_container"; do
        [[ -z "$(docker ps -aq --filter "name=^/${unexpected}$")" ]] \
            || die "Unexpected pre-existing DB05 container: $unexpected"
    done
    [[ -z "$(docker volume ls -q --filter "name=^${target_volume}$")" ]] \
        || die "Canonical target volume already exists"
    [[ -z "$(docker network ls -q --filter "name=^${target_network}$")" ]] \
        || die "Target restore network already exists"
else
    for unexpected in "$source_rollback_container" "$source_holder" "$target_held_container"; do
        [[ -z "$(docker ps -aq --filter "name=^/${unexpected}$")" ]] \
            || die "Unexpected resume container: $unexpected"
    done
    [[ "$(docker inspect "$maintenance_container" --format '{{.Image}}|{{.State.Status}}')" == "$expected_caddy_image_id|running" ]] \
        || die "Maintenance container differs at resume"
    [[ "$(docker inspect "$server_container" --format '{{.State.Status}}')" == "exited" ]] \
        || die "Application writers are not stopped at resume"
    [[ "$(docker inspect "$caddy_container" --format '{{.State.Status}}')" == "exited" ]] \
        || die "Original Caddy is not stopped at resume"
    [[ "$(docker inspect "$target_temporary_container" --format '{{.Image}}|{{.State.Status}}')" == "$expected_image_id|running" ]] \
        || die "Restored target container differs at resume"
    [[ "$(docker inspect "$target_temporary_container" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')" == "$target_volume" ]] \
        || die "Restored target volume differs at resume"
    [[ -z "$(docker port "$target_temporary_container")" ]] \
        || die "Restored target publishes a host port at resume"
    [[ -f "$evidence_dir/target-restore-result" ]] \
        || die "Verified target restore result is absent at resume"
    grep -Fx 'table_fingerprints=exact' "$evidence_dir/target-restore-result" >/dev/null \
        || die "Target restore fingerprints were not exact"
    grep -Fx 'schema=exact' "$evidence_dir/target-restore-result" >/dev/null \
        || die "Target restore schema was not exact"
fi

available_bytes="$(df -PB1 /var/lib/docker | awk 'NR == 2 {print $4}')"
((available_bytes >= 120 * 1024 * 1024 * 1024)) \
    || die "Insufficient Docker capacity for production cutover"

production_user="$(capture_container_environment "$source_container" POSTGRES_USER)"
production_password="$(capture_container_environment "$source_container" POSTGRES_PASSWORD)"
production_database="$(capture_container_environment "$source_container" POSTGRES_DB)"
[[ -n "$production_user" && -n "$production_password" && -n "$production_database" ]] \
    || die "Production database environment is incomplete"
bootstrap_user="uwa_db05_restore_$(date +%s)"
bootstrap_password="$(openssl rand -base64 48 | tr -d '\n')"
bootstrap_database="${bootstrap_user}_bootstrap"
{
    printf 'POSTGRES_USER=%s\n' "$bootstrap_user"
    printf 'POSTGRES_PASSWORD=%s\n' "$bootstrap_password"
    printf 'POSTGRES_DB=%s\n' "$bootstrap_database"
} >"$runtime_dir/target-postgres.env"
{
    printf 'POSTGRES_USER=%s\n' "$production_user"
    printf 'POSTGRES_PW=%s\n' "$production_password"
    printf 'POSTGRES_DB=%s\n' "$production_database"
    printf 'DJANGO_SECRET_KEY=%s\n' "$(openssl rand -base64 48 | tr -d '\n')"
    printf 'DEBUG=False\n'
    printf 'APP_ENVIRONMENT=production\n'
} >"$runtime_dir/application.env"
{
    printf 'POSTGRES_USER=%s\n' "$production_user"
    printf 'POSTGRES_PASSWORD=%s\n' "$production_password"
    printf 'POSTGRES_DB=%s\n' "$production_database"
} >"$runtime_dir/source-postgres.env"
chmod 600 "$runtime_dir"/*.env

if [[ "$resume_after_target_restore" == "false" ]]; then
log INFO "Installing external HTTP 503 maintenance response"
cat >"$runtime_dir/Caddyfile.maintenance" <<'CADDY'
{
    email brandon.xu@wsu.edu
}

firewisewatersheds.org, unstable.wepp.cloud {
    respond "Utility Watershed Analytics maintenance" 503
}
CADDY
docker stop --time 30 "$caddy_container" >/dev/null
docker run --detach \
    --name "$maintenance_container" \
    --label com.utility-watershed-analytics.db05-production=true \
    --mount "type=bind,source=$runtime_dir/Caddyfile.maintenance,destination=/etc/caddy/Caddyfile,readonly" \
    --mount type=volume,source=utility-watershed-analytics_caddy_data,destination=/data \
    --publish 80:80 \
    --publish 443:443 \
    "$expected_caddy_image_id" >/dev/null
for attempt in $(seq 1 30); do
    local_status="$(curl --insecure --silent --output /dev/null --write-out '%{http_code}' \
        --resolve firewisewatersheds.org:443:127.0.0.1 \
        https://firewisewatersheds.org/ || true)"
    [[ "$local_status" == "503" ]] && break
    sleep 1
done
[[ "$local_status" == "503" ]] || die "Local HTTPS maintenance response did not return 503"
write_state maintenance-awaiting-external-approval
log INFO "Maintenance is locally verified; waiting for external approval gate"
for attempt in $(seq 1 120); do
    [[ -f "$maintenance_gate" ]] && break
    sleep 5
done
[[ -f "$maintenance_gate" ]] || die "External maintenance approval gate timed out"
write_state maintenance-approved

log INFO "Stopping application writers and proving quiescence"
docker stop --time 30 "$server_container" >/dev/null
[[ "$(active_writer_count)" == "0" ]] || die "Active database writer remains"
capture_inventory "$source_container" "$production_user" "$production_database" \
    "$runtime_dir/quiescence-before"
sleep 10
[[ "$(active_writer_count)" == "0" ]] || die "Writer appeared during quiescence interval"
capture_inventory "$source_container" "$production_user" "$production_database" \
    "$runtime_dir/quiescence-after"
for inventory in extensions.tsv migrations.tsv sequences.tsv table-fingerprints.tsv; do
    cmp --silent "$runtime_dir/quiescence-before/$inventory" \
        "$runtime_dir/quiescence-after/$inventory" \
        || die "Database inventory drifted during quiescence: $inventory"
done
write_state quiescent

log INFO "Creating fresh encrypted off-host pre-cutover backup"
set -a
source "$backup_profile"
set +a
BACKUP_RELEASE_ID="db05-pre-$(date -u +'%Y%m%dT%H%M%SZ')" \
    "$installed_backup_root/scripts/run_scheduled_backup.sh" \
    | tee "$evidence_dir/pre-cutover-backup.log"
cp -- "$BACKUP_STATE_DIR/last-success" "$evidence_dir/pre-cutover-last-success"
pre_snapshot_id="$(awk -F= '$1 == "snapshot_id" {print $2}' "$evidence_dir/pre-cutover-last-success")"
backup_set_name="$(awk -F= '$1 == "backup_set_name" {print $2}' "$evidence_dir/pre-cutover-last-success")"
[[ "$pre_snapshot_id" =~ ^[0-9a-f]{64}$ ]] || die "Fresh pre-cutover snapshot ID is invalid"
backup_set="$BACKUP_OUTPUT_DIR/$backup_set_name"
[[ -d "$backup_set" && -f "$backup_set/complete" ]] || die "Fresh backup set is unavailable"
write_state pre-cutover-backup-passed

log INFO "Restoring fresh backup into canonical named target volume"
docker volume create \
    --label com.utility-watershed-analytics.db05-production=true \
    --label com.utility-watershed-analytics.prune=prohibited \
    "$target_volume" >/dev/null
docker network create --internal "$target_network" >/dev/null
docker run --detach \
    --name "$target_temporary_container" \
    --network "$target_network" \
    --network-alias db \
    --label com.utility-watershed-analytics.restore-target=true \
    --label com.utility-watershed-analytics.db05-production=true \
    --env-file "$runtime_dir/target-postgres.env" \
    --mount "type=volume,source=$target_volume,destination=/var/lib/postgresql/data" \
    "$expected_image_id" >/dev/null
wait_for_database "$target_temporary_container" "$bootstrap_user" postgres \
    || die "Named restore target did not become ready"
[[ -z "$(docker port "$target_temporary_container")" ]] \
    || die "Named restore target unexpectedly publishes a host port"
RESTORE_RESULT_FILE="$evidence_dir/target-restore-result" \
    "$script_input/restore_database.sh" \
    --backup-set "$backup_set" \
    --target-container "$target_temporary_container"
run_smoke "$target_network" "$evidence_dir/target-restore-smoke.log"
write_state target-restore-passed
else
    log INFO "Resuming from exact verified target restore"
    set -a
    source "$backup_profile"
    set +a
    cp -- "$BACKUP_STATE_DIR/last-success" "$evidence_dir/pre-cutover-last-success"
    pre_snapshot_id="$(awk -F= '$1 == "snapshot_id" {print $2}' "$evidence_dir/pre-cutover-last-success")"
    backup_set_name="$(awk -F= '$1 == "backup_set_name" {print $2}' "$evidence_dir/pre-cutover-last-success")"
    [[ "$pre_snapshot_id" =~ ^[0-9a-f]{64}$ ]] || die "Resume snapshot ID is invalid"
    backup_set="$BACKUP_OUTPUT_DIR/$backup_set_name"
    [[ -d "$backup_set" && -f "$backup_set/complete" ]] \
        || die "Resume backup set is unavailable"
    run_smoke "$target_network" "$evidence_dir/target-restore-smoke.log"
    write_state target-restore-passed
fi

log INFO "Installing reviewed Compose target and preserving anonymous source"
sudo cp --preserve=mode,ownership,timestamps -- "$canonical_compose" \
    "$evidence_dir/compose.prod.pre-db05.yml"
sudo install -o roger -g roger -m 0644 -- "$compose_input" "$canonical_compose"
sudo docker compose \
    --project-name "$project" \
    --env-file "$runtime_environment" \
    --file "$canonical_compose" \
    config --format json >"$runtime_dir/compose-target.json"
python3 - "$runtime_dir/compose-target.json" <<'PY' \
    || die "Rendered target violates the named-volume or socket contract"
import json
import sys

with open(sys.argv[1], encoding="utf-8") as config_stream:
    database = json.load(config_stream)["services"]["db"]
mounts = database.get("volumes") or []
if not any(
    mount.get("target") == "/var/lib/postgresql/data"
    and mount.get("source") == "postgres_data"
    for mount in mounts
):
    raise SystemExit("canonical database mount is absent")
if database.get("ports"):
    raise SystemExit("database publishes a host port")
PY
shred --remove --zero "$runtime_dir/compose-target.json"
sudo docker compose \
    --project-name "$project" \
    --env-file "$runtime_environment" \
    --file "$canonical_compose" \
    --dry-run up --detach --no-build --pull never db \
    >"$evidence_dir/compose-cutover-dry-run.log" 2>&1
grep -Eiq 'postgis.*(recreat|creat)' "$evidence_dir/compose-cutover-dry-run.log" \
    || die "Compose cutover dry-run did not identify the expected database replacement"
grep -Eiq 'pull|build' "$evidence_dir/compose-cutover-dry-run.log" \
    && die "Compose cutover dry-run proposed pull or build"

docker create \
    --name "$source_holder" \
    --label com.utility-watershed-analytics.db05-source-holder=true \
    --label com.utility-watershed-analytics.prune=prohibited \
    --mount "type=volume,source=$expected_source_volume,destination=/var/lib/postgresql/data" \
    --entrypoint /bin/true \
    "$expected_image_id" >/dev/null
docker inspect "$source_container" \
    | python3 -c '
import json
import sys
record = json.load(sys.stdin)[0]
record.get("Config", {}).pop("Env", None)
json.dump(record, sys.stdout, indent=2, sort_keys=True)
print()
' >"$evidence_dir/source-container-inspect-sanitized.json"
docker stop --time 30 "$source_container" >/dev/null
docker container rm "$source_container" >/dev/null
docker stop --time 30 "$target_temporary_container" >/dev/null
docker container rm "$target_temporary_container" >/dev/null
docker network rm "$target_network" >/dev/null

cutover_epoch="$(date +%s)"
sudo docker compose \
    --project-name "$project" \
    --env-file "$runtime_environment" \
    --file "$canonical_compose" \
    up --detach --no-build --pull never db
wait_for_database "$source_container" "$production_user" "$production_database" \
    || die "Canonical named database did not become ready"
[[ "$(docker inspect "$source_container" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')" == "$target_volume" ]] \
    || die "Canonical database did not mount the named target"
[[ -z "$(docker port "$source_container")" ]] \
    || die "Canonical named database unexpectedly publishes a host port"
run_smoke "$project_network" "$evidence_dir/cutover-smoke.log"
cutover_duration_seconds=$(($(date +%s) - cutover_epoch))
((cutover_duration_seconds <= maximum_rto_seconds)) || die "Cutover exceeded maximum RTO"
write_state cutover-passed

log INFO "Exercising actual rollback to the held anonymous source"
rollback_epoch="$(date +%s)"
docker stop --time 30 "$source_container" >/dev/null
docker rename "$source_container" "$target_held_container"
docker network disconnect "$project_network" "$target_held_container"
docker run --detach \
    --name "$source_rollback_container" \
    --network "$project_network" \
    --network-alias db \
    --restart unless-stopped \
    --publish 5432:5432 \
    --env-file "$runtime_dir/source-postgres.env" \
    --mount "type=volume,source=$expected_source_volume,destination=/var/lib/postgresql/data" \
    --health-cmd "pg_isready -U $production_user -d $production_database" \
    --health-interval 5s \
    --health-timeout 5s \
    --health-retries 5 \
    --health-start-period 30s \
    "$expected_image_id" >/dev/null
wait_for_database "$source_rollback_container" "$production_user" "$production_database" \
    || die "Anonymous source rollback did not become ready"
run_smoke "$project_network" "$evidence_dir/rollback-smoke.log"
rollback_duration_seconds=$(($(date +%s) - rollback_epoch))
((rollback_duration_seconds <= maximum_rto_seconds)) || die "Rollback exceeded maximum RTO"
write_state rollback-passed

log INFO "Reapplying accepted named target"
reapply_epoch="$(date +%s)"
docker stop --time 30 "$source_rollback_container" >/dev/null
docker container rm "$source_rollback_container" >/dev/null
docker network connect --alias db "$project_network" "$target_held_container"
docker rename "$target_held_container" "$source_container"
docker start "$source_container" >/dev/null
wait_for_database "$source_container" "$production_user" "$production_database" \
    || die "Named target did not become ready after reapply"
run_smoke "$project_network" "$evidence_dir/reapply-smoke.log"
reapply_duration_seconds=$(($(date +%s) - reapply_epoch))
((reapply_duration_seconds <= maximum_rto_seconds)) || die "Reapply exceeded maximum RTO"
write_state reapply-passed

log INFO "Proving named-volume restart and Compose recreation persistence"
docker restart --time 30 "$source_container" >/dev/null
wait_for_database "$source_container" "$production_user" "$production_database" \
    || die "Named target failed restart persistence"
docker stop --time 30 "$source_container" >/dev/null
docker container rm "$source_container" >/dev/null
sudo docker compose \
    --project-name "$project" \
    --env-file "$runtime_environment" \
    --file "$canonical_compose" \
    up --detach --no-build --pull never db
wait_for_database "$source_container" "$production_user" "$production_database" \
    || die "Named target failed container recreation persistence"
run_smoke "$project_network" "$evidence_dir/recreation-smoke.log"

capture_inventory "$source_container" "$production_user" "$production_database" \
    "$runtime_dir/final-inventory"
for inventory in extensions.tsv migrations.tsv sequences.tsv table-fingerprints.tsv; do
    cmp --silent "$backup_set/inventory/$inventory" "$runtime_dir/final-inventory/$inventory" \
        || die "Final named target inventory differs: $inventory"
done

log INFO "Capturing final identity and installing immutable safe runtime bundle"
"$script_input/database_identity.sh" capture \
    --container "$source_container" \
    --output "$evidence_dir/database-identity.named"
sudo install -o root -g root -m 0600 \
    "$evidence_dir/database-identity.named" "$database_identity"
sudo install -d -o root -g root -m 0755 "$bundle_root/scripts"
for helper in check_runtime_environment.sh database_identity.sh start_runtime.sh \
    with_operation_lock.sh; do
    sudo install -o root -g root -m 0755 "$script_input/$helper" "$bundle_root/scripts/$helper"
done
sed "s#/workdir/utility-watershed-analytics/scripts#$bundle_root/scripts#g" \
    "$unit_input" >"$evidence_dir/utility-watershed-analytics.db05.service"
sudo install -o root -g root -m 0644 \
    "$evidence_dir/utility-watershed-analytics.db05.service" \
    /etc/systemd/system/utility-watershed-analytics.service
sudo systemctl daemon-reload

log INFO "Restoring application and normal Caddy routing"
docker start "$server_container" >/dev/null
sleep 5
docker container rm --force "$maintenance_container" >/dev/null
docker start "$caddy_container" >/dev/null
for attempt in $(seq 1 60); do
    public_status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
        https://firewisewatersheds.org/api/watershed/aversive-forestry/ || true)"
    [[ "$public_status" == "200" ]] && break
    sleep 2
done
[[ "$public_status" == "200" ]] || die "Public API did not recover after maintenance"

final_container_id="$(docker inspect "$source_container" --format '{{.Id}}')"
total_duration_seconds=$(($(date +%s) - cutover_started_epoch))
result_partial="$(mktemp "$evidence_dir/.cutover-result.XXXXXX")"
{
    printf 'status=ready-for-systemd-restart-and-reboot\n'
    printf 'source_container_id=%s\n' "$expected_container_id"
    printf 'source_volume=%s\n' "$expected_source_volume"
    printf 'source_holder=%s\n' "$source_holder"
    printf 'target_container_id=%s\n' "$final_container_id"
    printf 'target_volume=%s\n' "$target_volume"
    printf 'pre_cutover_snapshot_id=%s\n' "$pre_snapshot_id"
    printf 'cutover_duration_seconds=%s\n' "$cutover_duration_seconds"
    printf 'rollback_duration_seconds=%s\n' "$rollback_duration_seconds"
    printf 'reapply_duration_seconds=%s\n' "$reapply_duration_seconds"
    printf 'maintenance_http_status=503\n'
    printf 'write_quiescence=passed\n'
    printf 'restart_persistence=passed\n'
    printf 'container_recreation_persistence=passed\n'
    printf 'final_inventory=exact\n'
    printf 'public_api_status=200\n'
    printf 'total_duration_seconds=%s\n' "$total_duration_seconds"
} >"$result_partial"
mv -- "$result_partial" "$result_file"
shred --remove --zero "$runtime_dir/application.env" \
    "$runtime_dir/source-postgres.env" "$runtime_dir/target-postgres.env"
write_state ready-for-systemd-restart-and-reboot
trap - EXIT
log INFO "DB05 cutover phase passed; release lock before systemd restart"
