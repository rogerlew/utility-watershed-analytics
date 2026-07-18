#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
original_arguments=("$@")

if [[ -z "${UWA_OPERATION_LOCK_FD:-}" ]]; then
    exec "$script_dir/with_operation_lock.sh" --mode exclusive -- \
        "$0" "${original_arguments[@]}"
fi

"$script_dir/require_operation_lock.sh" exclusive >/dev/null
exec python3 "$script_dir/deploy_database.py" "$@"
