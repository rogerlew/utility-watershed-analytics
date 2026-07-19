#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'

readonly expected_host=wepp3
readonly configuration=/etc/utility-watershed-analytics/artifact-proxy.Caddyfile
readonly expected_configuration_sha256=9c5f4a8aeb24e1f6dffd94d4e210b90b40b1e19bce1513f6056d147b84689831
readonly manifest=bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5
readonly origin_uri="http://100.87.36.38:18080/v1/production/objects/sha256/bb/$manifest"
readonly public_uri="https://firewisewatersheds.org/artifacts/v1/production/objects/sha256/bb/$manifest"

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

[[ "$(hostname)" == "$expected_host" ]] || die "wrong host"
[[ "$EUID" -eq 0 ]] || die "root is required"
[[ -f "$configuration" && ! -L "$configuration" ]] || die "configuration is missing"
[[ "$(stat -c '%a %U:%G' "$configuration")" == "600 root:root" ]] \
    || die "configuration permissions differ"
[[ "$(sha256sum "$configuration" | awk '{print $1}')" == "$expected_configuration_sha256" ]] \
    || die "configuration SHA-256 differs"
[[ "$(curl -fsS "$origin_uri" | sha256sum | awk '{print $1}')" == "$manifest" ]] \
    || die "private origin manifest differs"

mapfile -t caddy_containers < <(
    docker ps \
        --filter label=com.docker.compose.project=utility-watershed-analytics \
        --filter label=com.docker.compose.service=caddy \
        --format '{{.Names}}'
)
[[ "${#caddy_containers[@]}" -eq 1 ]] || die "expected exactly one production Caddy container"
caddy_container="${caddy_containers[0]}"

docker exec -i "$caddy_container" \
    caddy validate --config - --adapter caddyfile <"$configuration"
docker exec -i "$caddy_container" \
    caddy reload --config - --adapter caddyfile <"$configuration"

for attempt in $(seq 1 30); do
    observed_manifest="$(curl -fsS "$public_uri" | sha256sum | awk '{print $1}')" || true
    [[ "$observed_manifest" == "$manifest" ]] && break
    [[ "$attempt" != 30 ]] || die "public manifest did not converge"
    sleep 1
done
curl -fsS -o /dev/null https://firewisewatersheds.org/
printf 'artifact proxy active configuration_sha256=%s manifest_sha256=%s\n' \
    "$expected_configuration_sha256" "$manifest"
