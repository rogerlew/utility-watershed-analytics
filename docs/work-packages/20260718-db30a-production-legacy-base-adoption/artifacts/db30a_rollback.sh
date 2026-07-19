#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly repository=/workdir/utility-watershed-analytics
readonly operation=/tmp/uwa-db30a-operation
readonly image=uwa-server:db30a
readonly manifest=bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5

cd "$repository"
scripts/require_operation_lock.sh exclusive
[[ "$(hostname)" == wepp3 ]]

database_container="$({ docker ps --filter label=com.docker.compose.project=utility-watershed-analytics --filter label=com.docker.compose.service=db --format '{{.Names}}'; } | head -1)"
database_user="$(docker exec "$database_container" printenv POSTGRES_USER)"
database_name="$(docker exec "$database_container" printenv POSTGRES_DB)"
database_password="$(docker exec "$database_container" printenv POSTGRES_PASSWORD)"
oneoff_secret="$(head -c 48 /dev/urandom | base64 | tr -d '\n')"

run_executor() {
    docker run --rm \
        --user "$(id -u):$(id -g)" \
        --network utility-watershed-analytics_default \
        --env POSTGRES_USER="$database_user" \
        --env POSTGRES_PW="$database_password" \
        --env POSTGRES_DB="$database_name" \
        --env DJANGO_SECRET_KEY="$oneoff_secret" \
        --env DEBUG=False \
        --env APP_ENVIRONMENT=production \
        --volume "$operation/db30a_operations.py:/ops.py:ro" \
        --volume "$operation/reviewed/db28:/reviewed/db28:ro" \
        --volume "$operation/artifacts:/artifacts:ro" \
        "$image" "$@"
}

run_executor python manage.py rollback_legacy_adoption \
    --root /artifacts \
    --manifest-sha256 "$manifest" \
    | tee "$operation/evidence/production-rollback-result.json"

run_executor python /ops.py state \
    --input-root /reviewed/db28 \
    --artifact-root /artifacts \
    | tee "$operation/evidence/production-rollback-state.json"

python3 - "$operation/evidence/production-rollback-state.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    state = json.load(stream)
assert state["active_state"] == "EMPTY"
assert state["active_release"] is None
assert state["active_manifest_sha256"] is None
assert state["watersheds"] == 126
assert state["subcatchments"] == 195457
assert state["channels"] == 86895
assert state["identities"] == 126
assert state["aliases"] == 313
assert state["releases"] == 1
assert state["capabilities"] == 0
PY

printf 'DB30A production rollback complete.\n'
