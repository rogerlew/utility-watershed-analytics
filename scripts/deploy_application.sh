#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
compose_file="${UWA_COMPOSE_FILE:-$repo_root/compose.prod.yml}"
project_name="${UWA_COMPOSE_PROJECT:-utility-watershed-analytics}"
environment_file="${UWA_RUNTIME_ENV_FILE:-/etc/utility-watershed-analytics/runtime.env}"
healthcheck_url="${DEPLOY_HEALTHCHECK_URL:-}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Build and deploy application services while preserving the exact PostgreSQL
container, image, project labels, and data volume. The command self-acquires
the exclusive host-wide operations lock when it is not already inherited.

Options:
  --compose-file PATH
  --project-name NAME
  --env-file PATH
  --healthcheck-url HTTPS_URL
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
        --healthcheck-url)
            (($# >= 2)) || die "--healthcheck-url requires a value"
            healthcheck_url="$2"
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
    || die "Application deployment requires an exclusive operations lock"

for required_command in awk basename curl dirname docker grep id mktemp python3 rm stat; do
    command -v "$required_command" >/dev/null 2>&1 \
        || die "Required command not found: $required_command"
done
[[ -x "$script_dir/database_identity.sh" ]] \
    || die "Database identity helper is unavailable"
[[ -x "$script_dir/check_runtime_environment.sh" ]] \
    || die "Runtime environment checker is unavailable"
[[ -f "$compose_file" && -r "$compose_file" ]] \
    || die "Compose file is unavailable: $compose_file"
[[ -f "$environment_file" && -r "$environment_file" ]] \
    || die "Runtime environment file is unavailable: $environment_file"
"$script_dir/check_runtime_environment.sh" \
    --env-file "$environment_file" \
    --expected-uid "$(id -u)"
if [[ -n "$healthcheck_url" ]]; then
    [[ "$healthcheck_url" == https://* ]] \
        || die "Deployment health check must use HTTPS"
fi

runtime_dir="$(mktemp -d /tmp/uwa-application-deploy.XXXXXX)"
cleanup() {
    rm -rf -- "$runtime_dir"
}
trap cleanup EXIT
identity_file="$runtime_dir/database-identity"
rendered_config="$runtime_dir/compose.json"
dry_run_report="$runtime_dir/dry-run.txt"

compose=(
    docker compose
    --project-name "$project_name"
    --env-file "$environment_file"
    --file "$compose_file"
)

"$script_dir/database_identity.sh" capture \
    --container postgis \
    --output "$identity_file"

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

"${compose[@]}" --dry-run up --detach --no-deps server caddy \
    >"$dry_run_report" 2>&1 \
    || die "Compose dry-run failed"
if grep -Eiq '(postgis|(^|[[:space:]])db([[:space:]]|$)).*(create|recreate|remove|stop|replace)' \
    "$dry_run_report"; then
    die "Compose dry-run proposes a database action"
fi

"${compose[@]}" build server frontend-build
"${compose[@]}" run --rm --no-deps \
    --entrypoint python server manage.py migrate --noinput
"${compose[@]}" run --rm --no-deps frontend-build
"${compose[@]}" up --detach --no-deps server caddy

"$script_dir/database_identity.sh" assert \
    --container postgis \
    --expected "$identity_file"
"${compose[@]}" ps server caddy

if [[ -n "$healthcheck_url" ]]; then
    curl --fail --silent --show-error \
        --retry 10 \
        --retry-all-errors \
        --retry-delay 3 \
        --max-time 20 \
        --output /dev/null \
        "$healthcheck_url"
fi

trap - EXIT
cleanup
printf 'Application deployment passed with unchanged database identity\n'
