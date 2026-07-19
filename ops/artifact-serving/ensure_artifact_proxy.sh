#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'

readonly repository=/workdir/utility-watershed-analytics
readonly base_compose="$repository/compose.prod.yml"
readonly override_compose=/etc/utility-watershed-analytics/compose.artifact-proxy.yml
readonly expected_override_sha256=e07abadc6a127df07dd2bee7759f6aa76d6fa59fffae3ab1e64079b42e82cdcf
readonly runtime_environment=/etc/utility-watershed-analytics/runtime.env
readonly project=utility-watershed-analytics
readonly apply_script=/usr/local/lib/utility-watershed-analytics-artifact-serving/apply_artifact_proxy.sh

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

[[ "$(hostname)" == wepp3 ]] || die "wrong host"
[[ "$EUID" -eq 0 ]] || die "root is required"
[[ -f "$override_compose" && ! -L "$override_compose" ]] || die "Compose override is missing"
[[ "$(stat -c '%a %U:%G' "$override_compose")" == "600 root:root" ]] \
    || die "Compose override permissions differ"
[[ "$(sha256sum "$override_compose" | awk '{print $1}')" == "$expected_override_sha256" ]] \
    || die "Compose override SHA-256 differs"

compose=(
    docker compose
    --project-name "$project"
    --env-file "$runtime_environment"
    --file "$base_compose"
    --file "$override_compose"
)
"${compose[@]}" config --quiet
"${compose[@]}" up --detach --no-build --no-deps --pull never server caddy
"$apply_script"

mapfile -t caddy_containers < <(
    docker ps \
        --filter label=com.docker.compose.project="$project" \
        --filter label=com.docker.compose.service=caddy \
        --format '{{.Names}}'
)
[[ "${#caddy_containers[@]}" -eq 1 ]] || die "expected exactly one production Caddy container"
mounted_source="$(
    docker inspect "${caddy_containers[0]}" \
        --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}'
)"
[[ "$mounted_source" == /etc/utility-watershed-analytics/artifact-proxy.Caddyfile ]] \
    || die "Caddy configuration mount differs"
printf 'artifact proxy container mount active source=%s\n' "$mounted_source"
