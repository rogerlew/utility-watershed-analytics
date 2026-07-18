#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

phase="${1:-}"
request_file="${2:-}"
state_file="${3:-}"
operation_dir="${4:-}"
secret_file="${5:-}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

[[ -n "$phase" && -f "$request_file" && -f "$state_file" \
    && -d "$operation_dir" && -f "$secret_file" ]] \
    || die "Database deployment phase arguments are incomplete"
phase_root="${UWA_DB_DEPLOY_PHASE_ROOT:-/usr/local/lib/utility-watershed-analytics/database-deployment-phases}"
phase_program="$phase_root/$phase"
[[ "$phase" =~ ^[a-z][a-z_]*$ ]] || die "Invalid phase name"
[[ -d "$phase_root" && ! -L "$phase_root" ]] \
    || die "Deployment phase root is not an ordinary directory"
[[ -x "$phase_program" && ! -L "$phase_program" ]] \
    || die "Reviewed deployment phase is not installed: $phase"
if [[ "$phase_root" != "/usr/local/lib/utility-watershed-analytics/database-deployment-phases" \
    && "${UWA_DB_DEPLOY_TEST_MODE:-}" != "1" ]]; then
    die "A custom phase root is allowed only in explicit test mode"
fi
if [[ "${UWA_DB_DEPLOY_TEST_MODE:-}" != "1" ]]; then
    [[ "$(stat -c '%u' -- "$phase_root" "$phase_program")" == $'0\n0' ]] \
        || die "Deployment phase root and program must be root-owned"
    phase_mode="$(stat -c '%a' -- "$phase_program")"
    (( (8#$phase_mode & 8#022) == 0 )) \
        || die "Deployment phase program must not be group/world writable"
fi

exec "$phase_program" "$request_file" "$state_file" "$operation_dir" "$secret_file"
