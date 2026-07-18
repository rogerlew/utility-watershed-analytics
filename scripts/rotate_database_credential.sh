#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077
export LC_ALL=C

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
container="postgis"
database=""
admin_user=""
role=""
password_file=""

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

while (($# > 0)); do
    case "$1" in
        --container) container="$2"; shift 2 ;;
        --database) database="$2"; shift 2 ;;
        --admin-user) admin_user="$2"; shift 2 ;;
        --role) role="$2"; shift 2 ;;
        --password-file) password_file="$2"; shift 2 ;;
        -h|--help)
            printf 'Usage: %s --database DB --admin-user USER --role ROLE --password-file PATH [--container NAME]\n' "$(basename "$0")"
            exit 0
            ;;
        *) die "Unknown option: $1" ;;
    esac
done

case "$role" in
    uwa_status_login|uwa_staging_login|uwa_activation_login|uwa_runtime_login|uwa_backup_login|uwa_migration_login|uwa_restore_login) ;;
    *) die "Role is not a DB25 credential principal" ;;
esac
[[ "$container" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || die "Container name is invalid"
[[ "$database" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || die "Database name is invalid"
[[ "$admin_user" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || die "Admin user is invalid"
[[ -f "$password_file" && ! -L "$password_file" ]] || die "Password file is invalid"
[[ "$(stat --format '%a' "$password_file")" == "600" ]] || die "Password file must have mode 0600"
[[ "$(stat --format '%u' "$password_file")" == "$(id -u)" ]] || die "Password file has the wrong owner"
[[ "$(wc -l <"$password_file")" == "0" ]] || die "Password file must contain exactly one unterminated value"
password="$(cat -- "$password_file")"
[[ ${#password} -ge 16 && ${#password} -le 1024 ]] || die "Password length is outside the accepted range"
[[ "$password" != *[![:print:]]* ]] || die "Password contains a non-printing byte"
escaped_password="${password//\'/\'\'}"
"$script_dir/require_operation_lock.sh" exclusive >/dev/null

printf "ALTER ROLE %s PASSWORD '%s';\n" "$role" "$escaped_password" \
    | docker exec --interactive "$container" \
        psql --no-psqlrc --set ON_ERROR_STOP=1 --username "$admin_user" --dbname "$database" \
        >/dev/null
unset password escaped_password

printf 'Database credential rotated: role=%s\n' "$role"
