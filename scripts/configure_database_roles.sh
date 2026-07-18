#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
container="postgis"
database=""
admin_user=""

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

while (($# > 0)); do
    case "$1" in
        --container) container="$2"; shift 2 ;;
        --database) database="$2"; shift 2 ;;
        --admin-user) admin_user="$2"; shift 2 ;;
        -h|--help)
            printf 'Usage: %s --database DB --admin-user USER [--container NAME]\n' "$(basename "$0")"
            exit 0
            ;;
        *) die "Unknown option: $1" ;;
    esac
done

[[ "$container" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || die "Container name is invalid"
[[ "$database" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || die "Database name is invalid"
[[ "$admin_user" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || die "Admin user is invalid"
"$script_dir/require_operation_lock.sh" exclusive >/dev/null
[[ -f "$script_dir/database_roles.sql" && ! -L "$script_dir/database_roles.sql" ]] \
    || die "Database role contract is unavailable"

docker exec --interactive "$container" \
    psql --no-psqlrc --set ON_ERROR_STOP=1 --username "$admin_user" --dbname "$database" \
    <"$script_dir/database_roles.sql"

printf 'Database role contract applied without credential values\n'
