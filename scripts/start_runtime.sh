#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
compose_file="${UWA_COMPOSE_FILE:-$repo_root/compose.prod.yml}"
project_name="${UWA_COMPOSE_PROJECT:-utility-watershed-analytics}"
environment_file="${UWA_RUNTIME_ENV_FILE:-/etc/utility-watershed-analytics/runtime.env}"
identity_file="${UWA_DATABASE_IDENTITY_FILE:-/etc/utility-watershed-analytics/database-identity}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Start the canonical production runtime while preserving the exact existing
PostgreSQL container, image, project labels, and data volume.

Options:
  --compose-file PATH
  --project-name NAME
  --env-file PATH
  --identity-file PATH
  -h, --help
EOF
}

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

original_arguments=("$@")
while (($# > 0)); do
    case "$1" in
        --compose-file)
            (($# >= 2)) || die "--compose-file requires a value"
            compose_file="$2"
            shift 2
            ;;
        --project-name)
            (($# >= 2)) || die "--project-name requires a value"
            project_name="$2"
            shift 2
            ;;
        --env-file)
            (($# >= 2)) || die "--env-file requires a value"
            environment_file="$2"
            shift 2
            ;;
        --identity-file)
            (($# >= 2)) || die "--identity-file requires a value"
            identity_file="$2"
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

if [[ -z "${UWA_OPERATION_LOCK_FD:-}" ]]; then
    exec "$script_dir/with_operation_lock.sh" --mode exclusive -- \
        "$0" "${original_arguments[@]}"
fi
[[ "${UWA_OPERATION_LOCK_MODE:-}" == "exclusive" ]] \
    || die "Runtime start requires an exclusive operations lock"

for required_command in awk docker grep id mktemp python3 rm stat; do
    command -v "$required_command" >/dev/null 2>&1 \
        || die "Required command not found: $required_command"
done
[[ -x "$script_dir/check_runtime_environment.sh" ]] \
    || die "Runtime environment checker is unavailable"
[[ -x "$script_dir/database_identity.sh" ]] \
    || die "Database identity helper is unavailable"
[[ -f "$compose_file" && -r "$compose_file" ]] \
    || die "Compose file is unavailable: $compose_file"
[[ -f "$identity_file" && ! -L "$identity_file" ]] \
    || die "Database identity must be a regular non-symlink file"
[[ "$(stat --format '%a' "$identity_file")" == "600" ]] \
    || die "Database identity file must have mode 0600"
[[ "$(stat --format '%u' "$identity_file")" == "$(id -u)" ]] \
    || die "Database identity file has the wrong owner"

"$script_dir/check_runtime_environment.sh" \
    --env-file "$environment_file" \
    --expected-uid "$(id -u)"

runtime_dir="$(mktemp -d /tmp/uwa-runtime-start.XXXXXX)"
cleanup() {
    rm -rf -- "$runtime_dir"
}
trap cleanup EXIT
rendered_config="$runtime_dir/compose.json"
dry_run_report="$runtime_dir/dry-run.txt"

compose=(
    docker compose
    --project-name "$project_name"
    --env-file "$environment_file"
    --file "$compose_file"
)

"$script_dir/database_identity.sh" assert \
    --container postgis \
    --expected "$identity_file"

"${compose[@]}" config --format json >"$rendered_config"
planned_database_image="$(python3 - "$rendered_config" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as config_stream:
    config = json.load(config_stream)
print(config["services"]["db"]["image"])
PY
)"
[[ "$planned_database_image" =~ @sha256:[0-9a-f]{64}$ ]] \
    || die "Rendered production database image is not pinned by repository digest"
planned_database_image_id="$(docker image inspect --format '{{.Id}}' "$planned_database_image")" \
    || die "Pinned production database image is unavailable locally"
expected_database_image_id="$(awk -F= '$1 == "image_id" {print substr($0, index($0, "=") + 1)}' "$identity_file")"
[[ "$planned_database_image_id" == "$expected_database_image_id" ]] \
    || die "Pinned Compose image does not match the running database image"

"${compose[@]}" --dry-run up --detach --no-build --no-recreate --pull never \
    db server caddy >"$dry_run_report" 2>&1 \
    || die "Compose runtime dry-run failed"
if grep -Eiq 'postgis.*(creat|recreat|remov|replac|pull|build|stop)' "$dry_run_report"; then
    die "Compose runtime dry-run proposes a database create or replacement action"
fi

"${compose[@]}" up --detach --no-build --no-recreate --pull never \
    db server caddy

"$script_dir/database_identity.sh" assert \
    --container postgis \
    --expected "$identity_file"

trap - EXIT
cleanup
printf 'Canonical runtime start passed with unchanged database identity\n'
