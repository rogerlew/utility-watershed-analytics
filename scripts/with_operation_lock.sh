#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 007

readonly DEFAULT_LOCK_FILE="/run/lock/utility-watershed-analytics/operations.lock"
readonly DEFAULT_TIMEOUT_SECONDS="60"

lock_file="${UWA_OPERATION_LOCK_FILE:-$DEFAULT_LOCK_FILE}"
lock_mode="exclusive"
timeout_seconds="${UWA_OPERATION_LOCK_TIMEOUT_SECONDS:-$DEFAULT_TIMEOUT_SECONDS}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options] -- COMMAND [ARGUMENT ...]

Run one operation under the canonical host-wide lock. A nested invocation
inherits the outer descriptor and cannot upgrade a shared lock to exclusive.

Options:
  --mode shared|exclusive   Lock mode (default: exclusive)
  --timeout SECONDS        Bounded acquisition wait (default: 60)
  --lock-file PATH         Test override; production uses $DEFAULT_LOCK_FILE
  -h, --help               Show this help
EOF
}

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

while (($# > 0)); do
    case "$1" in
        --mode)
            (($# >= 2)) || die "--mode requires a value"
            lock_mode="$2"
            shift 2
            ;;
        --timeout)
            (($# >= 2)) || die "--timeout requires a value"
            timeout_seconds="$2"
            shift 2
            ;;
        --lock-file)
            (($# >= 2)) || die "--lock-file requires a value"
            lock_file="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown option before --: $1"
            ;;
    esac
done

[[ "$lock_mode" == "shared" || "$lock_mode" == "exclusive" ]] \
    || die "--mode must be shared or exclusive"
[[ "$timeout_seconds" =~ ^[0-9]+([.][0-9]+)?$ ]] \
    || die "--timeout must be a non-negative number of seconds"
(($# > 0)) || die "A command is required after --"
[[ "$lock_file" == /* ]] || die "Lock file must be an absolute path"
[[ "$lock_file" != *$'\n'* ]] || die "Lock path must not contain a newline"

for required_command in flock readlink realpath; do
    command -v "$required_command" >/dev/null 2>&1 \
        || die "Required command not found: $required_command"
done

run_child() {
    local child_pid
    local child_status

    "$@" &
    child_pid=$!

    terminate_child() {
        kill -TERM "$child_pid" >/dev/null 2>&1 || true
        wait "$child_pid" >/dev/null 2>&1 || true
        exit 143
    }
    interrupt_child() {
        kill -INT "$child_pid" >/dev/null 2>&1 || true
        wait "$child_pid" >/dev/null 2>&1 || true
        exit 130
    }
    trap terminate_child TERM HUP
    trap interrupt_child INT

    set +e
    wait "$child_pid"
    child_status=$?
    set -e
    trap - TERM HUP INT
    return "$child_status"
}

if [[ -n "${UWA_OPERATION_LOCK_FD:-}" ]]; then
    [[ "$UWA_OPERATION_LOCK_FD" =~ ^[0-9]+$ ]] \
        || die "Inherited lock descriptor is invalid"
    [[ "${UWA_OPERATION_LOCK_MODE:-}" == "shared" \
        || "${UWA_OPERATION_LOCK_MODE:-}" == "exclusive" ]] \
        || die "Inherited lock mode is invalid"
    inherited_path="$(readlink "/proc/$$/fd/$UWA_OPERATION_LOCK_FD")" \
        || die "Inherited lock descriptor is not open"
    expected_path="$(realpath -- "$lock_file")" \
        || die "Canonical lock file is unavailable: $lock_file"
    [[ "$inherited_path" == "$expected_path" ]] \
        || die "Inherited descriptor does not reference the canonical lock"
    if [[ "$UWA_OPERATION_LOCK_MODE" == "shared" && "$lock_mode" == "exclusive" ]]; then
        die "A shared outer lock cannot be upgraded by a nested operation"
    fi
    run_child "$@"
    exit $?
fi

[[ -f "$lock_file" && ! -L "$lock_file" ]] \
    || die "Canonical lock file must be a pre-provisioned regular file: $lock_file"
lock_file="$(realpath -- "$lock_file")"

exec {lock_fd}<>"$lock_file"
if [[ "$lock_mode" == "shared" ]]; then
    flock --shared --timeout "$timeout_seconds" "$lock_fd" \
        || die "Timed out acquiring shared operations lock: $lock_file"
else
    flock --exclusive --timeout "$timeout_seconds" "$lock_fd" \
        || die "Timed out acquiring exclusive operations lock: $lock_file"
fi

export UWA_OPERATION_LOCK_FD="$lock_fd"
export UWA_OPERATION_LOCK_FILE="$lock_file"
export UWA_OPERATION_LOCK_MODE="$lock_mode"

run_child "$@"
