#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
lock_script="$repo_root/scripts/with_operation_lock.sh"
fixture_dir="$(mktemp -d /tmp/uwa-operation-lock-test.XXXXXX)"
lock_file="$fixture_dir/operations.lock"
cd -- "$repo_root"

cleanup() {
    find "$fixture_dir" -type f -delete
    find "$fixture_dir" -depth -type d -empty -delete
}
trap cleanup EXIT

install -m 660 /dev/null "$lock_file"

wait_for_file() {
    local path="$1"
    local remaining=50
    while ((remaining > 0)); do
        [[ -e "$path" ]] && return 0
        sleep 0.1
        remaining=$((remaining - 1))
    done
    printf 'Timed out waiting for fixture: %s\n' "$path" >&2
    return 1
}

"$lock_script" --lock-file "$lock_file" --mode exclusive -- bash -c '
    scripts/with_operation_lock.sh --mode shared -- true
    scripts/with_operation_lock.sh --mode exclusive -- true
'

set +e
"$lock_script" --lock-file "$lock_file" --mode shared -- bash -c '
    scripts/with_operation_lock.sh --mode exclusive -- true
' >"$fixture_dir/upgrade.stdout" 2>"$fixture_dir/upgrade.stderr"
upgrade_status=$?
set -e
[[ "$upgrade_status" -ne 0 ]]

exclusive_ready="$fixture_dir/exclusive-ready"
"$lock_script" --lock-file "$lock_file" --mode exclusive -- \
    bash -c "touch \"\$1\"; sleep 2" fixture "$exclusive_ready" &
exclusive_pid=$!
wait_for_file "$exclusive_ready"
set +e
"$lock_script" --lock-file "$lock_file" --mode shared --timeout 0.2 -- true \
    >"$fixture_dir/contention.stdout" 2>"$fixture_dir/contention.stderr"
contention_status=$?
set -e
[[ "$contention_status" -ne 0 ]]
wait "$exclusive_pid"

shared_ready="$fixture_dir/shared-ready"
"$lock_script" --lock-file "$lock_file" --mode shared -- \
    bash -c "touch \"\$1\"; sleep 1" fixture "$shared_ready" &
shared_pid=$!
wait_for_file "$shared_ready"
"$lock_script" --lock-file "$lock_file" --mode shared --timeout 0.2 -- true
wait "$shared_pid"

cancel_ready="$fixture_dir/cancel-ready"
"$lock_script" --lock-file "$lock_file" --mode exclusive -- \
    bash -c "touch \"\$1\"; sleep 30" fixture "$cancel_ready" &
cancel_pid=$!
wait_for_file "$cancel_ready"
kill -TERM "$cancel_pid"
set +e
wait "$cancel_pid"
cancel_status=$?
set -e
[[ "$cancel_status" -eq 143 ]]
"$lock_script" --lock-file "$lock_file" --mode exclusive --timeout 1 -- true

set +e
UWA_OPERATION_LOCK_FD=999 \
UWA_OPERATION_LOCK_FILE="$lock_file" \
UWA_OPERATION_LOCK_MODE=exclusive \
    "$lock_script" --mode shared -- true \
    >"$fixture_dir/stale.stdout" 2>"$fixture_dir/stale.stderr"
stale_status=$?
set -e
[[ "$stale_status" -ne 0 ]]

printf 'nested=passed\n'
printf 'shared_to_exclusive_upgrade=rejected\n'
printf 'exclusive_contention=rejected\n'
printf 'concurrent_shared=passed\n'
printf 'cancellation_status=%s\n' "$cancel_status"
printf 'post_cancellation_reacquire=passed\n'
printf 'stale_descriptor=rejected\n'
