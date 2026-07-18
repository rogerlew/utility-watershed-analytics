#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'

required_mode="${1:-exclusive}"
lock_file="${UWA_OPERATION_LOCK_FILE:-/run/lock/utility-watershed-analytics/operations.lock}"
lock_fd="${UWA_OPERATION_LOCK_FD:-}"
lock_mode="${UWA_OPERATION_LOCK_MODE:-}"

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

[[ "$required_mode" == "shared" || "$required_mode" == "exclusive" ]] \
    || die "Required lock mode must be shared or exclusive"
[[ "$lock_fd" =~ ^[0-9]+$ ]] || die "Inherited operations lock descriptor is absent"
[[ "$lock_mode" == "shared" || "$lock_mode" == "exclusive" ]] \
    || die "Inherited operations lock mode is invalid"
if [[ "$required_mode" == "exclusive" && "$lock_mode" != "exclusive" ]]; then
    die "An exclusive operations lock is required"
fi
[[ "$lock_file" == /* ]] || die "Operations lock path must be absolute"
[[ -f "$lock_file" && ! -L "$lock_file" ]] \
    || die "Canonical operations lock is unavailable"

inherited_path="$(readlink "/proc/$$/fd/$lock_fd")" \
    || die "Inherited operations lock descriptor is closed"
expected_path="$(realpath -- "$lock_file")" \
    || die "Canonical operations lock cannot be resolved"
[[ "$inherited_path" == "$expected_path" ]] \
    || die "Inherited descriptor does not reference the canonical operations lock"

printf 'Canonical %s operations lock is held\n' "$lock_mode"
