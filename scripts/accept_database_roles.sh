#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
container=""
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
            printf 'Usage: %s --container NAME --database DB --admin-user USER\n' "$(basename "$0")"
            exit 0
            ;;
        *) die "Unknown option: $1" ;;
    esac
done

[[ "${DB25_DISPOSABLE_ACCEPTANCE:-}" == "true" ]] \
    || die "DB25_DISPOSABLE_ACCEPTANCE=true is required"
[[ "$container" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || die "Container name is invalid"
[[ "$database" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || die "Database name is invalid"
[[ "$admin_user" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || die "Admin user is invalid"
"$script_dir/require_operation_lock.sh" exclusive >/dev/null
command -v openssl >/dev/null 2>&1 || die "OpenSSL is required"
database_host="$(docker exec "$container" hostname -i | awk '{print $1}')"
[[ "$database_host" =~ ^[0-9a-fA-F:.]+$ ]] || die "Disposable database address is invalid"

temporary_dir="$(mktemp -d /tmp/uwa-db25-roles.XXXXXX)"
cleanup() {
    find "$temporary_dir" -type f -delete
    find "$temporary_dir" -depth -type d -empty -delete
}
trap cleanup EXIT

roles=(status staging activation runtime backup migration restore)
declare -A old_passwords=()
declare -A new_passwords=()

make_password() {
    openssl rand -hex 32
}

rotate() {
    local role="$1"
    local password="$2"
    local password_file="$temporary_dir/$role.password"
    printf '%s' "$password" >"$password_file"
    chmod 0600 "$password_file"
    "$script_dir/rotate_database_credential.sh" \
        --container "$container" \
        --database "$database" \
        --admin-user "$admin_user" \
        --role "uwa_${role}_login" \
        --password-file "$password_file" >/dev/null
    find "$password_file" -delete
}

sql() {
    local role="$1"
    local password="$2"
    local statement="$3"
    local password_path="/tmp/uwa-db25-${role}.pgpass"
    local status=0
    printf '*:*:%s:uwa_%s_login:%s\n' "$database" "$role" "$password" \
        | docker exec --interactive "$container" sh -c \
            'umask 077; cat >"$1"' fixture "$password_path"
    docker exec --env "PGPASSFILE=$password_path" "$container" \
        psql --no-psqlrc --set ON_ERROR_STOP=1 --host "$database_host" \
        --username "uwa_${role}_login" --dbname "$database" \
        --command "$statement" >/dev/null || status=$?
    docker exec "$container" find "$password_path" -delete
    return "$status"
}

denied() {
    local role="$1"
    local password="$2"
    local statement="$3"
    if sql "$role" "$password" "$statement" \
        >"$temporary_dir/denied.stdout" 2>"$temporary_dir/denied.stderr"; then
        die "Expected database denial for role: $role"
    fi
}

for role in "${roles[@]}"; do
    old_passwords[$role]="$(make_password)"
    new_passwords[$role]="$(make_password)"
    rotate "$role" "${old_passwords[$role]}"
    sql "$role" "${old_passwords[$role]}" "SELECT 1"
    rotate "$role" "${new_passwords[$role]}"
    denied "$role" "${old_passwords[$role]}" "SELECT 1"
    sql "$role" "${new_passwords[$role]}" "SELECT 1"
done

sql status "${new_passwords[status]}" "SELECT count(*) FROM watershed_activedatarelease"
denied status "${new_passwords[status]}" "UPDATE watershed_activedatarelease SET state = state WHERE false"
denied status "${new_passwords[status]}" "SELECT count(*) FROM auth_user"
denied status "${new_passwords[status]}" "SET ROLE uwa_activation"

sql runtime "${new_passwords[runtime]}" "SELECT count(*) FROM watershed_watershed"
denied runtime "${new_passwords[runtime]}" "UPDATE watershed_watershed SET runid = runid WHERE false"
denied runtime "${new_passwords[runtime]}" "SELECT count(*) FROM watershed_stagedwatershed"

sql staging "${new_passwords[staging]}" "UPDATE watershed_datareleasestagingstate SET updated_at = updated_at WHERE false"
denied staging "${new_passwords[staging]}" "UPDATE watershed_watershed SET runid = runid WHERE false"
denied staging "${new_passwords[staging]}" "UPDATE watershed_activedatarelease SET state = state WHERE false"

sql activation "${new_passwords[activation]}" "UPDATE watershed_watershed SET runid = runid WHERE false"
sql activation "${new_passwords[activation]}" "UPDATE watershed_activedatarelease SET state = state WHERE false"
denied activation "${new_passwords[activation]}" "CREATE TABLE db25_forbidden(id integer)"

sql backup "${new_passwords[backup]}" "SELECT count(*) FROM auth_user"
denied backup "${new_passwords[backup]}" "UPDATE watershed_watershed SET runid = runid WHERE false"

sql migration "${new_passwords[migration]}" \
    "CREATE TABLE db25_migration_probe(id integer); DROP TABLE db25_migration_probe"

denied restore "${new_passwords[restore]}" "SELECT count(*) FROM watershed_watershed"
sql restore "${new_passwords[restore]}" \
    "SET ROLE uwa_restore; CREATE TABLE db25_restore_probe(id integer); DROP TABLE db25_restore_probe"

audit_settings="$(docker exec "$container" psql --no-psqlrc --tuples-only --no-align \
    --username "$admin_user" --dbname "$database" \
    --command "SELECT array_to_string(rolconfig, ',') FROM pg_roles WHERE rolname = 'uwa_restore_login'")"
[[ "$audit_settings" == *"log_statement=all"* && "$audit_settings" == *"log_duration=on"* ]] \
    || die "Restore credential does not force statement audit logging"

printf 'Database role acceptance passed: roles=%s rotations=%s\n' \
    "${#roles[@]}" "${#roles[@]}"
