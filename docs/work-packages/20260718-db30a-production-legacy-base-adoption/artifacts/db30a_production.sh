#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly repository=/workdir/utility-watershed-analytics
readonly operation=/tmp/uwa-db30a-operation
readonly evidence="$operation/evidence"
readonly image=uwa-server:db30a
readonly image_digest=sha256:9c902ab226daf0d848bd3fa2012495e5375a036c5b5adcd645974eafb9c4215c
readonly materializer_digest=sha256:301f91b2a6bba1ead732830e542a51ce5f4fddaae2e862046c38a134fcc5747b
readonly manifest=bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5
readonly plan_sha=276b57ac1eb6b11b4a607cb8140bb86229ebef11040e3fd2a1f9772472e4275c
readonly application_commit=5b358c14fffa258f5ec9f1ab55d3645b225888c1
readonly materializer_commit=22647350b9163587485239af1c28e5430937af49

cd "$repository"
scripts/require_operation_lock.sh exclusive
[[ "$(hostname)" == wepp3 ]]
[[ -z "$(git status --short)" ]]
[[ "$(git rev-parse HEAD)" == "$application_commit" ]]
[[ "$(docker image inspect "$image" --format '{{.Id}}')" == "$image_digest" ]]
[[ "$(sha256sum "$operation/reviewed-adoption-plan.json" | awk '{print $1}')" == "$plan_sha" ]]
[[ "$(sha256sum "$operation/reviewed-identity.json" | awk '{print $1}')" == 9e49204f3f83e9c1b44e2608927a6a7627011710bb4c09e9f0794e574acce54b ]]
install -d -m 700 "$evidence"

database_container="$({ docker ps --filter label=com.docker.compose.project=utility-watershed-analytics --filter label=com.docker.compose.service=db --format '{{.Names}}'; } | head -1)"
[[ -n "$database_container" ]]
database_user="$(docker exec "$database_container" printenv POSTGRES_USER)"
database_name="$(docker exec "$database_container" printenv POSTGRES_DB)"
database_password="$(docker exec "$database_container" printenv POSTGRES_PASSWORD)"
oneoff_secret="$(head -c 48 /dev/urandom | base64 | tr -d '\n')"
[[ -n "$database_user" && -n "$database_name" && -n "$database_password" ]]

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
        --volume "$operation/reviewed-identity.json:/reviewed/identity.json:ro" \
        --volume "$operation/artifacts:/artifacts:rw" \
        "$image" "$@"
}

assert_json() {
    python3 - "$@" <<'PY'
import json
import sys

phase = sys.argv[1]
with open(sys.argv[2], encoding="utf-8") as stream:
    current = json.load(stream)
before = None
if len(sys.argv) > 3:
    with open(sys.argv[3], encoding="utf-8") as stream:
        before = json.load(stream)

if phase == "before":
    assert current == {
        **current,
        "active_state": "EMPTY",
        "active_release": None,
        "active_manifest_sha256": None,
        "watersheds": 126,
        "subcatchments": 195457,
        "channels": 86895,
        "identities": 126,
        "aliases": 126,
        "releases": 0,
        "capabilities": 0,
    }
elif phase == "export":
    assert current["status"] == "exported"
    assert current["manifest_sha256"] == "bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5"
    assert current["members"] == 126
    assert current["counts"] == {
        "capabilities": 3,
        "channels": 86895,
        "subcatchments": 195457,
        "watersheds": 126,
    }
elif phase == "post-export":
    assert current["active_state"] == "EMPTY"
    assert current["active_release"] is None
    assert current["watersheds"] == 126
    assert current["subcatchments"] == 195457
    assert current["channels"] == 86895
    assert current["identities"] == 126
    assert current["aliases"] == 313
    assert current["releases"] == 0
    assert current["capabilities"] == 0
    assert current["business_fingerprints"] == before["business_fingerprints"]
elif phase == "after":
    assert current["active_state"] == "ACTIVE"
    assert current["active_release"] == "2026-07-18.30"
    assert current["active_manifest_sha256"] == "bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5"
    assert current["watersheds"] == 126
    assert current["subcatchments"] == 195457
    assert current["channels"] == 86895
    assert current["identities"] == 126
    assert current["aliases"] == 313
    assert current["releases"] == 1
    assert current["capabilities"] == 3
    assert current["business_fingerprints"] == before["business_fingerprints"]
else:
    raise AssertionError(f"unknown assertion phase: {phase}")
PY
}

scripts/database_inventory.sh \
    --container "$database_container" \
    --database "$database_name" \
    --user "$database_user" \
    --output-dir "$evidence/production-before"

run_executor python /ops.py state \
    --input-root /reviewed/db28 \
    --artifact-root /artifacts \
    | tee "$evidence/production-before-state.json"

assert_json before "$evidence/production-before-state.json"

run_executor python /ops.py export \
    --input-root /reviewed/db28 \
    --artifact-root /artifacts \
    --identity-mapping /reviewed/identity.json \
    --release-id 2026-07-18.30 \
    --materializer-git-commit "$materializer_commit" \
    --materializer-image-digest "$materializer_digest" \
    | tee "$evidence/production-export-result.json"

assert_json export "$evidence/production-export-result.json"

run_executor python /ops.py state \
    --input-root /reviewed/db28 \
    --artifact-root /artifacts \
    | tee "$evidence/production-post-export-state.json"

assert_json post-export \
    "$evidence/production-post-export-state.json" \
    "$evidence/production-before-state.json"

run_executor python manage.py adopt_legacy_base \
    --root /artifacts \
    --manifest-sha256 "$manifest" \
    --actor roger-db30a-production \
    --application-git-commit "$application_commit" \
    --reviewed-plan-sha256 "$plan_sha" \
    | tee "$evidence/production-adoption-result.json"

run_executor python /ops.py verify-active \
    --input-root /reviewed/db28 \
    --artifact-root /artifacts \
    --manifest-sha256 "$manifest" \
    | tee "$evidence/production-active-verification.json"

run_executor python /ops.py state \
    --input-root /reviewed/db28 \
    --artifact-root /artifacts \
    | tee "$evidence/production-after-state.json"

assert_json after \
    "$evidence/production-after-state.json" \
    "$evidence/production-before-state.json"

scripts/database_inventory.sh \
    --container "$database_container" \
    --database "$database_name" \
    --user "$database_user" \
    --output-dir "$evidence/production-after"

printf 'DB30A production adoption complete.\n'
