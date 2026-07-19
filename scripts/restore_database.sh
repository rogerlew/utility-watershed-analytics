#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
backup_set=""
target_container=""
result_file="${RESTORE_RESULT_FILE:-}"
allow_compatible_image=0

usage() {
    cat <<EOF
Usage: $(basename "$0") --backup-set PATH --target-container NAME [options]

Restore one completed backup set into an explicitly labeled disposable
PostGIS container and compare roles, extensions, migrations, sequences,
schema, and table fingerprints.

Required target label:
  com.utility-watershed-analytics.restore-target=true

Options:
  --backup-set PATH          Completed backup-set directory
  --target-container NAME   Disposable running PostGIS container
  --allow-compatible-image  Permit a different image ID when PostgreSQL major
                            and PostGIS versions match the backup metadata
  -h, --help                Show this help

Environment:
  RESTORE_RESULT_FILE       Optional mode-0600 result file written atomically
EOF
}

log() {
    printf '%s [%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2"
}

die() {
    log ERROR "$1" >&2
    exit 1
}

while (($# > 0)); do
    case "$1" in
        --backup-set)
            (($# >= 2)) || die "--backup-set requires a value"
            backup_set="$2"
            shift 2
            ;;
        --target-container)
            (($# >= 2)) || die "--target-container requires a value"
            target_container="$2"
            shift 2
            ;;
        --allow-compatible-image)
            allow_compatible_image=1
            shift
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

[[ -n "$backup_set" ]] || die "--backup-set is required"
[[ -n "$target_container" ]] || die "--target-container is required"
[[ "$backup_set" != *$'\n'* ]] || die "Backup-set path must not contain a newline"
[[ "$result_file" != *$'\n'* ]] || die "Restore result path must not contain a newline"

for command in awk basename cmp date dirname docker grep mktemp mv python3 \
    realpath rm sha256sum; do
    command -v "$command" >/dev/null 2>&1 || die "Required command not found: $command"
done
[[ -x "$script_dir/database_inventory.sh" ]] \
    || die "Database inventory helper is not executable: $script_dir/database_inventory.sh"

backup_set="$(realpath -- "$backup_set")"
[[ -d "$backup_set" ]] || die "Backup set not found: $backup_set"
for path in complete checksums.sha256 metadata.txt database.dump globals.sql \
    schema.sql inventory; do
    [[ -e "$backup_set/$path" ]] || die "Backup set is incomplete; missing: $path"
done

log INFO "Verifying backup-set checksums"
(
    cd -- "$backup_set"
    sha256sum --check checksums.sha256
) || die "Backup-set checksum verification failed"

metadata_value() {
    local key="$1"
    awk -F= -v key="$key" '$1 == key {print substr($0, index($0, "=") + 1); found=1} END {if (!found) exit 1}' \
        "$backup_set/metadata.txt"
}

source_container="$(metadata_value container)" \
    || die "Backup metadata is missing source container"
source_database="$(metadata_value database)" \
    || die "Backup metadata is missing database"
source_image_id="$(metadata_value container_image_id)" \
    || die "Backup metadata is missing image ID"
source_server_version="$(metadata_value postgres_server_version)" \
    || die "Backup metadata is missing PostgreSQL version"
source_postgis_version="$(metadata_value postgis_version)" \
    || die "Backup metadata is missing PostGIS version"

[[ "$target_container" != "$source_container" ]] \
    || die "Refusing to restore into the source container: $target_container"
docker inspect "$target_container" >/dev/null 2>&1 \
    || die "Target container not found: $target_container"
[[ "$(docker inspect --format '{{.State.Running}}' "$target_container")" == "true" ]] \
    || die "Target container is not running: $target_container"
target_label="$(docker inspect --format '{{ index .Config.Labels "com.utility-watershed-analytics.restore-target" }}' "$target_container")"
[[ "$target_label" == "true" ]] \
    || die "Target container lacks the required disposable restore-target label"

target_image_id="$(docker inspect --format '{{.Image}}' "$target_container")"
if [[ "$target_image_id" != "$source_image_id" && "$allow_compatible_image" != 1 ]]; then
    die "Target image ID differs from the source; use --allow-compatible-image only after compatibility review"
fi

target_user="$(docker exec "$target_container" sh -ceu 'printf "%s" "${POSTGRES_USER:?}"')"
[[ -n "$target_user" ]] || die "Target POSTGRES_USER is empty"
docker exec "$target_container" pg_isready --quiet \
    --username "$target_user" --dbname postgres \
    || die "Target PostgreSQL is not ready"

target_server_version="$(
    docker exec "$target_container" psql -X -qAt --no-password \
        --username "$target_user" --dbname postgres \
        --command 'SHOW server_version;'
)"
source_server_major="${source_server_version%%.*}"
target_server_major="${target_server_version%%.*}"
[[ "$target_server_major" == "$source_server_major" ]] \
    || die "PostgreSQL major mismatch: source=$source_server_version target=$target_server_version"

database_exists="$(
    printf "SELECT count(*) FROM pg_database WHERE datname = :'source_database';\n" \
    | docker exec -i "$target_container" psql -X -qAt --no-password \
        --username "$target_user" --dbname postgres \
        --set ON_ERROR_STOP=1 \
        --variable "source_database=$source_database"
)"
[[ "$database_exists" == "0" ]] \
    || die "Target already contains the source database: $source_database"

started_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
restore_started_seconds=$SECONDS

log INFO "Restoring cluster globals into disposable target"
python3 - "$backup_set/globals.sql" <<'PY' \
    | docker exec -i "$target_container" psql -X --no-password \
        --username "$target_user" --dbname postgres \
        --set ON_ERROR_STOP=1 \
    || die "Cluster-global restore failed"
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
with source.open(encoding="utf-8") as stream:
    for line in stream:
        if line.startswith("GRANT ") and " GRANTED BY " in line:
            statement, grantor = line.rsplit(" GRANTED BY ", 1)
            if not grantor.endswith(";\n"):
                raise SystemExit("unsupported GRANTED BY statement in globals dump")
            line = statement + ";\n"
        sys.stdout.write(line)
PY

log INFO "Restoring database archive into disposable target"
docker exec -i "$target_container" pg_restore \
    --create \
    --exit-on-error \
    --no-password \
    --username "$target_user" \
    --dbname postgres \
    <"$backup_set/database.dump" \
    || die "Database restore failed"

restored_postgis_version="$(
    docker exec "$target_container" psql -X -qAt --no-password \
        --username "$target_user" --dbname "$source_database" \
        --set ON_ERROR_STOP=1 \
        --command "SELECT extversion FROM pg_extension WHERE extname = 'postgis';"
)"
[[ "$restored_postgis_version" == "$source_postgis_version" ]] \
    || die "PostGIS mismatch: source=$source_postgis_version restored=$restored_postgis_version"

comparison_dir="$(mktemp -d /tmp/uwa-restore-inventory.XXXXXX)"
cleanup() {
    rm -rf -- "$comparison_dir"
}
trap cleanup EXIT

"$script_dir/database_inventory.sh" \
    --container "$target_container" \
    --database "$source_database" \
    --user "$target_user" \
    --output-dir "$comparison_dir"

assert_source_lines_present() {
    local source_file="$1"
    local restored_file="$2"
    local description="$3"
    while IFS= read -r expected_line; do
        grep -Fqx -- "$expected_line" "$restored_file" \
            || die "Restored $description is missing an expected source entry"
    done <"$source_file"
}

assert_source_lines_present \
    "$backup_set/inventory/roles.tsv" \
    "$comparison_dir/roles.tsv" \
    roles
assert_source_lines_present \
    "$backup_set/inventory/role-memberships.tsv" \
    "$comparison_dir/role-memberships.tsv" \
    role-memberships

for name in extensions.tsv migrations.tsv sequences.tsv table-fingerprints.tsv; do
    cmp --silent "$backup_set/inventory/$name" "$comparison_dir/$name" \
        || die "Restored inventory differs: $name"
done

restored_schema="$comparison_dir/schema.sql"
docker exec "$target_container" pg_dump \
    --host /var/run/postgresql \
    --username "$target_user" \
    --dbname "$source_database" \
    --schema-only \
    --no-password \
    >"$restored_schema"
schema_comparison="exact"
if ! cmp --silent "$backup_set/schema.sql" "$restored_schema"; then
    python3 - "$backup_set/schema.sql" "$restored_schema" <<'PY' \
        || die "Restored schema dump differs from the source schema dump"
import pathlib
import re
import sys


def normalized_schema(path):
    lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    normalized = []
    for line in lines:
        if " CONSTRAINT " in line and " CHECK " in line:
            line = line.replace("::character varying", "")
            line = line.replace("::text[]", "").replace("::text", "")
            line = line.replace("(", "").replace(")", "")
            line = re.sub(r"\s+", " ", line).strip()
        normalized.append(line)
    return normalized


if normalized_schema(sys.argv[1]) != normalized_schema(sys.argv[2]):
    raise SystemExit("schema differs outside equivalent CHECK rendering")
PY
    schema_comparison="normalized-equivalent-checks"
fi

restore_duration_seconds=$((SECONDS - restore_started_seconds))
completed_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

if [[ -n "$result_file" ]]; then
    result_parent="$(dirname -- "$result_file")"
    [[ -d "$result_parent" && -w "$result_parent" ]] \
        || die "Restore result directory is unavailable: $result_parent"
    result_partial="$(mktemp "$result_parent/.restore-result.XXXXXX")"
    {
        printf 'restore_started_utc=%s\n' "$started_at"
        printf 'restore_completed_utc=%s\n' "$completed_at"
        printf 'restore_duration_seconds=%s\n' "$restore_duration_seconds"
        printf 'source_database=%s\n' "$source_database"
        printf 'source_image_id=%s\n' "$source_image_id"
        printf 'target_image_id=%s\n' "$target_image_id"
        printf 'postgres_server_version=%s\n' "$target_server_version"
        printf 'postgis_version=%s\n' "$restored_postgis_version"
        printf 'roles=verified-source-subset\n'
        printf 'role_memberships=verified-source-subset\n'
        printf 'extensions=exact\n'
        printf 'migrations=exact\n'
        printf 'sequences=exact\n'
        printf 'table_fingerprints=exact\n'
        printf 'schema=%s\n' "$schema_comparison"
    } >"$result_partial"
    mv -- "$result_partial" "$result_file"
fi

trap - EXIT
cleanup

log INFO "Restore completed and all database comparisons passed"
log INFO "Restore duration: $restore_duration_seconds seconds"
log INFO "Target container: $target_container"
log INFO "Restored database: $source_database"
