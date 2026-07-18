#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
fixture_dir="$(mktemp -d /tmp/uwa-start-runtime-test.XXXXXX)"
cleanup() {
    rm -rf -- "$fixture_dir"
}
trap cleanup EXIT

fake_bin="$fixture_dir/bin"
mkdir -p "$fake_bin"
cat >"$fake_bin/docker" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

printf '%q ' "$@" >>"$FAKE_DOCKER_LOG"
printf '\n' >>"$FAKE_DOCKER_LOG"

if [[ "$1" == "inspect" ]]; then
    [[ "${FAKE_INSPECT_FAIL:-0}" == "0" ]] || exit 1
    cat "$FAKE_INSPECT_JSON"
    exit 0
fi
if [[ "$1" == "image" && "$2" == "inspect" ]]; then
    printf '%s\n' 'sha256:fixture-image'
    exit 0
fi
if [[ "$1" == "compose" ]]; then
    arguments=" $* "
    if [[ "$arguments" == *" config --format json "* ]]; then
        cat "$FAKE_COMPOSE_JSON"
        exit 0
    fi
    if [[ "$arguments" == *" --dry-run up "* ]]; then
        cat "$FAKE_DRY_RUN_REPORT"
        exit 0
    fi
    if [[ "$arguments" == *" up --detach "* ]]; then
        printf 'runtime-up\n'
        exit 0
    fi
    if [[ "$arguments" == *" build server frontend-build "* ]]; then
        exit 0
    fi
    if [[ "$arguments" == *" run --rm --no-deps "* ]]; then
        exit 0
    fi
    if [[ "$arguments" == *" ps server caddy "* ]]; then
        printf 'server running\ncaddy running\n'
        exit 0
    fi
fi
printf 'Unexpected fake Docker invocation: %s\n' "$*" >&2
exit 1
EOF
chmod 0755 "$fake_bin/docker"

cat >"$fixture_dir/inspect.json" <<'EOF'
[
  {
    "Id": "fixture-container",
    "Image": "sha256:fixture-image",
    "Name": "/postgis",
    "Config": {
      "Image": "postgis/postgis:fixture",
      "Labels": {
        "com.docker.compose.config-hash": "fixture-config",
        "com.docker.compose.project": "utility-watershed-analytics",
        "com.docker.compose.service": "db",
        "com.docker.compose.project.working_dir": "/workdir/utility-watershed-analytics"
      }
    },
    "Mounts": [
      {
        "Destination": "/var/lib/postgresql/data",
        "Driver": "local",
        "Name": "fixture-volume",
        "Source": "/var/lib/docker/volumes/fixture-volume/_data",
        "Type": "volume"
      }
    ]
  }
]
EOF
cat >"$fixture_dir/compose.json" <<'EOF'
{"services":{"db":{"image":"postgis/postgis@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}}
EOF
cat >"$fixture_dir/identity" <<'EOF'
compose_config_hash=fixture-config
compose_project=utility-watershed-analytics
compose_service=db
compose_working_dir=/workdir/utility-watershed-analytics
container_id=fixture-container
container_name=postgis
data_destination=/var/lib/postgresql/data
data_driver=local
data_mount_name=fixture-volume
data_mount_source=/var/lib/docker/volumes/fixture-volume/_data
data_mount_type=volume
image_id=sha256:fixture-image
image_reference=postgis/postgis:fixture
EOF
cat >"$fixture_dir/runtime.env" <<'EOF'
POSTGIS_IMAGE=postgis/postgis@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
POSTGRES_USER=fixture
POSTGRES_PW=fixture
POSTGRES_DB=fixture
DJANGO_SECRET_KEY=fixture
WEPPCLOUD_JWT_TOKEN=fixture
WEPPCLOUD_JWT_TOKEN_2=fixture
EOF
cat >"$fixture_dir/migration.env" <<'EOF'
POSTGRES_USER=uwa_migration_login
POSTGRES_PW=fixture-migration-only
POSTGRES_DB=fixture
EOF
cat >"$fixture_dir/compose.yml" <<'EOF'
services:
  db:
    image: ${POSTGIS_IMAGE}
EOF
printf 'Container postgis Running\n' >"$fixture_dir/dry-run.txt"
chmod 0600 "$fixture_dir/identity" "$fixture_dir/runtime.env" "$fixture_dir/migration.env"
touch "$fixture_dir/operations.lock"
chmod 0600 "$fixture_dir/operations.lock"

export PATH="$fake_bin:$PATH"
export FAKE_DOCKER_LOG="$fixture_dir/docker.log"
export FAKE_INSPECT_JSON="$fixture_dir/inspect.json"
export FAKE_COMPOSE_JSON="$fixture_dir/compose.json"
export FAKE_DRY_RUN_REPORT="$fixture_dir/dry-run.txt"
export UWA_OPERATION_LOCK_FILE="$fixture_dir/operations.lock"

"$repo_root/scripts/start_runtime.sh" \
    --compose-file "$fixture_dir/compose.yml" \
    --env-file "$fixture_dir/runtime.env" \
    --identity-file "$fixture_dir/identity"
grep -q -- '--no-build --no-recreate --pull never' "$fixture_dir/docker.log"
grep -q -- 'up --detach' "$fixture_dir/docker.log"

printf 'Container postgis Creating\n' >"$fixture_dir/dry-run.txt"
if "$repo_root/scripts/start_runtime.sh" \
    --compose-file "$fixture_dir/compose.yml" \
    --env-file "$fixture_dir/runtime.env" \
    --identity-file "$fixture_dir/identity" >/dev/null 2>&1; then
    printf 'Expected database-create dry-run rejection\n' >&2
    exit 1
fi

export FAKE_INSPECT_FAIL=1
if "$repo_root/scripts/start_runtime.sh" \
    --compose-file "$fixture_dir/compose.yml" \
    --env-file "$fixture_dir/runtime.env" \
    --identity-file "$fixture_dir/identity" >/dev/null 2>&1; then
    printf 'Expected missing database identity rejection\n' >&2
    exit 1
fi

export FAKE_INSPECT_FAIL=0
printf 'Container postgis Running\n' >"$fixture_dir/dry-run.txt"
: >"$fixture_dir/docker.log"
"$repo_root/scripts/deploy_application.sh" \
    --compose-file "$fixture_dir/compose.yml" \
    --env-file "$fixture_dir/runtime.env" \
    --migration-env-file "$fixture_dir/migration.env"
grep -q -- '--env-from-file' "$fixture_dir/docker.log"
grep -q -- 'migration.env' "$fixture_dir/docker.log"
grep -q -- 'manage.py migrate --noinput' "$fixture_dir/docker.log"
grep -q -- 'manage.py check_application_compatibility' "$fixture_dir/docker.log"

printf 'Runtime start fail-closed fixtures passed\n'
