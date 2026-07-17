#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

container=""
database=""
database_user=""
output_dir=""

usage() {
    cat <<EOF
Usage: $(basename "$0") --container NAME --database NAME --user NAME --output-dir PATH

Capture a secret-free logical inventory used to compare a PostgreSQL source
with an isolated restore. Existing output files are never overwritten.
EOF
}

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

while (($# > 0)); do
    case "$1" in
        --container)
            (($# >= 2)) || die "--container requires a value"
            container="$2"
            shift 2
            ;;
        --database)
            (($# >= 2)) || die "--database requires a value"
            database="$2"
            shift 2
            ;;
        --user)
            (($# >= 2)) || die "--user requires a value"
            database_user="$2"
            shift 2
            ;;
        --output-dir)
            (($# >= 2)) || die "--output-dir requires a value"
            output_dir="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done

[[ -n "$container" ]] || die "--container is required"
[[ -n "$database" ]] || die "--database is required"
[[ -n "$database_user" ]] || die "--user is required"
[[ -n "$output_dir" ]] || die "--output-dir is required"

for command in basename docker install mktemp mv rm; do
    command -v "$command" >/dev/null 2>&1 || die "Required command not found: $command"
done

docker inspect "$container" >/dev/null 2>&1 \
    || die "PostgreSQL container not found: $container"
[[ "$(docker inspect --format '{{.State.Running}}' "$container")" == "true" ]] \
    || die "PostgreSQL container is not running: $container"

if [[ ! -d "$output_dir" ]]; then
    install -d -m 700 -- "$output_dir"
fi
[[ -w "$output_dir" ]] || die "Output directory is not writable: $output_dir"

for name in roles.tsv role-memberships.tsv extensions.tsv migrations.tsv \
    sequences.tsv table-fingerprints.tsv; do
    [[ ! -e "$output_dir/$name" ]] || die "Refusing to overwrite: $output_dir/$name"
done

temporary_dir="$(mktemp -d "$output_dir/.inventory.XXXXXX")"
cleanup() {
    rm -rf -- "$temporary_dir"
}
trap cleanup EXIT

psql_query() {
    local target_database="$1"
    local sql="$2"
    docker exec "$container" psql \
        --no-password \
        --no-psqlrc \
        --quiet \
        --tuples-only \
        --no-align \
        --field-separator $'\t' \
        --set ON_ERROR_STOP=1 \
        --username "$database_user" \
        --dbname "$target_database" \
        --command "$sql"
}

psql_query postgres '
SELECT rolname,
       rolsuper,
       rolinherit,
       rolcreaterole,
       rolcreatedb,
       rolcanlogin,
       rolreplication,
       rolbypassrls,
       COALESCE(rolvaliduntil::text, $$ $$)
FROM pg_roles
ORDER BY rolname;
' >"$temporary_dir/roles.tsv"

psql_query postgres '
SELECT member.rolname,
       granted.rolname,
       membership.admin_option
FROM pg_auth_members AS membership
JOIN pg_roles AS member ON member.oid = membership.member
JOIN pg_roles AS granted ON granted.oid = membership.roleid
ORDER BY member.rolname, granted.rolname;
' >"$temporary_dir/role-memberships.tsv"

psql_query "$database" $'
SELECT extname, extversion
FROM pg_extension
ORDER BY extname;
' >"$temporary_dir/extensions.tsv"

if psql_query "$database" "SELECT to_regclass('public.django_migrations') IS NOT NULL;" \
    | tr -d '[:space:]' | grep -qx t; then
    psql_query "$database" $'
SELECT app, name
FROM django_migrations
ORDER BY app, name;
' >"$temporary_dir/migrations.tsv"
else
    : >"$temporary_dir/migrations.tsv"
fi

psql_query "$database" $'
SELECT schemaname,
       sequencename,
       start_value,
       min_value,
       max_value,
       increment_by,
       cycle,
       cache_size,
       COALESCE(last_value::text, $$ $$)
FROM pg_sequences
WHERE schemaname NOT IN ($$pg_catalog$$, $$information_schema$$)
ORDER BY schemaname, sequencename;
' >"$temporary_dir/sequences.tsv"

mapfile -t tables < <(
    psql_query "$database" $'
SELECT format($fmt$%I.%I$fmt$, schemaname, tablename)
FROM pg_tables
WHERE schemaname NOT IN ($$pg_catalog$$, $$information_schema$$)
ORDER BY schemaname, tablename;
'
)

: >"$temporary_dir/table-fingerprints.tsv"
for table in "${tables[@]}"; do
    [[ -n "$table" ]] || continue
    fingerprint="$({
        psql_query "$database" "
SELECT count(*),
       md5(
           count(*)::text || ':' ||
           COALESCE(sum(hashtextextended(row_to_json(inventory_row)::text, 0)::numeric), 0)::text
       )
FROM $table AS inventory_row;
"
    })"
    printf '%s\t%s\n' "$table" "$fingerprint" \
        >>"$temporary_dir/table-fingerprints.tsv"
done

for name in roles.tsv role-memberships.tsv extensions.tsv migrations.tsv \
    sequences.tsv table-fingerprints.tsv; do
    mv -- "$temporary_dir/$name" "$output_dir/$name"
done

trap - EXIT
rmdir -- "$temporary_dir"

printf 'Database inventory written to %s\n' "$output_dir"
