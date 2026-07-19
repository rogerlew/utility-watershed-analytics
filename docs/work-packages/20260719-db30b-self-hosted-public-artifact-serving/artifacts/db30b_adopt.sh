#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly repository=/workdir/utility-watershed-analytics
readonly operation=/tmp/uwa-db30b-operation
readonly evidence="$operation/evidence"
readonly image=uwa-server:db30a
readonly image_digest=sha256:9c902ab226daf0d848bd3fa2012495e5375a036c5b5adcd645974eafb9c4215c
readonly manifest=bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5
readonly plan_sha=994b8c96a0ba54068dba84fa70ec7c0ecadeeb57766f14423ed9c2921855db0b
readonly application_commit=5b358c14fffa258f5ec9f1ab55d3645b225888c1

cd "$repository"
scripts/require_operation_lock.sh exclusive
[[ "$(hostname)" == wepp3 ]]
[[ -z "$(git status --short)" ]]
[[ "$(git rev-parse HEAD)" == "$application_commit" ]]
[[ "$(docker image inspect "$image" --format '{{.Id}}')" == "$image_digest" ]]
[[ "$(sha256sum "$operation/reviewed-adoption-plan.json" | awk '{print $1}')" == "$plan_sha" ]]
[[ "$(curl -fsS "https://firewisewatersheds.org/artifacts/v1/production/objects/sha256/bb/$manifest" | sha256sum | awk '{print $1}')" == "$manifest" ]]
install -d -m 700 "$evidence"

mapfile -t database_containers < <(
    docker ps \
        --filter label=com.docker.compose.project=utility-watershed-analytics \
        --filter label=com.docker.compose.service=db \
        --format '{{.Names}}'
)
[[ "${#database_containers[@]}" -eq 1 ]]
database_container="${database_containers[0]}"
database_user="$(docker exec "$database_container" printenv POSTGRES_USER)"
database_name="$(docker exec "$database_container" printenv POSTGRES_DB)"
database_password="$(docker exec "$database_container" printenv POSTGRES_PASSWORD)"
oneoff_secret="$(head -c 48 /dev/urandom | base64 | tr -d '\n')"
operation_uid="$(stat -c '%u' "$operation")"
operation_gid="$(stat -c '%g' "$operation")"

run_executor() {
    docker run --rm \
        --user "$operation_uid:$operation_gid" \
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

assert_state() {
    python3 - "$1" "$2" <<'PY'
import json
import sys

phase, path = sys.argv[1:]
with open(path, encoding="utf-8") as stream:
    state = json.load(stream)
expected = {
    "watersheds": 126,
    "subcatchments": 195457,
    "channels": 86895,
    "identities": 126,
    "aliases": 313,
    "releases": 1,
}
for key, value in expected.items():
    assert state[key] == value, (key, state[key], value)
assert state["business_fingerprints"] == {
    "watershed": {"rows": 126, "fingerprint": "a2fd8b7ec1df3443f748c532ccf6a0ae"},
    "subcatchment": {"rows": 195457, "fingerprint": "f5fde1594f6881f2e3b0cf612eebbbea"},
    "channel": {"rows": 86895, "fingerprint": "eac27747bdbf18ac072c55fce612b62f"},
}
if phase == "before":
    assert state["active_state"] == "EMPTY"
    assert state["active_release"] is None
    assert state["active_manifest_sha256"] is None
    assert state["capabilities"] == 0
elif phase == "after":
    assert state["active_state"] == "ACTIVE"
    assert state["active_release"] == "2026-07-18.30"
    assert state["active_manifest_sha256"] == "bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5"
    assert state["capabilities"] == 3
else:
    raise AssertionError(f"unknown phase: {phase}")
PY
}

rollback_adoption() {
    set +e
    trap - ERR
    run_executor python manage.py rollback_legacy_adoption \
        --root /artifacts \
        --manifest-sha256 "$manifest" \
        >"$evidence/automatic-rollback-result.json" 2>"$evidence/automatic-rollback-error.log"
    rollback_status=$?
    run_executor python /ops.py state \
        --input-root /reviewed/db28 \
        --artifact-root /artifacts \
        >"$evidence/automatic-rollback-state.json" 2>>"$evidence/automatic-rollback-error.log"
    state_status=$?
    set -e
    if [[ "$rollback_status" -ne 0 || "$state_status" -ne 0 ]]; then
        printf 'automatic DB30A rollback failed\n' >&2
    else
        assert_state before "$evidence/automatic-rollback-state.json" || true
        printf 'automatic DB30A rollback completed\n' >&2
    fi
}

adopted=0
on_error() {
    exit_status=$?
    if [[ "$adopted" -eq 1 ]]; then
        rollback_adoption
    fi
    exit "$exit_status"
}
trap on_error ERR

scripts/database_inventory.sh \
    --container "$database_container" \
    --database "$database_name" \
    --user "$database_user" \
    --output-dir "$evidence/production-before"

run_executor python /ops.py state \
    --input-root /reviewed/db28 \
    --artifact-root /artifacts \
    | tee "$evidence/production-before-state.json"
assert_state before "$evidence/production-before-state.json"

run_executor python manage.py adopt_legacy_base \
    --root /artifacts \
    --manifest-sha256 "$manifest" \
    --actor roger-db30b-production \
    --application-git-commit "$application_commit" \
    --reviewed-plan-sha256 "$plan_sha" \
    | tee "$evidence/production-adoption-result.json"
adopted=1

run_executor python /ops.py verify-active \
    --input-root /reviewed/db28 \
    --artifact-root /artifacts \
    --manifest-sha256 "$manifest" \
    | tee "$evidence/production-active-verification.json"
run_executor python /ops.py state \
    --input-root /reviewed/db28 \
    --artifact-root /artifacts \
    | tee "$evidence/production-after-state.json"
assert_state after "$evidence/production-after-state.json"

gate_status="$(curl -sS -o "$evidence/gate-query.json" -w '%{http_code}' \
    -H 'Content-Type: application/json' \
    --data '{"kind":"choropleth","scenario":"S1","variable":"streamflow","spatial_scale":"hillslope","year":2000}' \
    https://firewisewatersheds.org/api/watershed/aversive-forestry/rhessys/query)"
[[ "$gate_status" == 200 ]]
python3 - "$evidence/gate-query.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    document = json.load(stream)
assert isinstance(document.get("rows"), list)
assert len(document["rows"]) == 173
PY

for run in Sooke09 Sooke15; do
    encoded="batch%3B%3Bvictoria-ca-2026-sbs%3B%3B$run"
    curl -fsS \
        "https://firewisewatersheds.org/api/watershed/$encoded/rhessys/outputs" \
        >"$evidence/${run,,}-catalog.json"
    curl -fsS \
        "https://firewisewatersheds.org/api/watershed/$encoded/rhessys/outputs/baseline/streamflow/tiles/0/0/0.png" \
        >"$evidence/${run,,}-tile.png"
    python3 - "$evidence/${run,,}-catalog.json" "$evidence/${run,,}-tile.png" <<'PY'
import json
import pathlib
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    catalog = json.load(stream)
assert catalog["capability"]["available"] is True
assert catalog["capability"]["source"] == "materialized"
assert pathlib.Path(sys.argv[2]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
PY
done

scripts/database_inventory.sh \
    --container "$database_container" \
    --database "$database_name" \
    --user "$database_user" \
    --output-dir "$evidence/production-after"

trap - ERR
printf 'DB30B retained baseline adoption and public capability checks complete.\n'
