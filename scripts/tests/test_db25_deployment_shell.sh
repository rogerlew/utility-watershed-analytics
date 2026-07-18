#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
fixture_dir="$(mktemp -d /tmp/uwa-db25-shell.XXXXXX)"
cleanup() {
    find "$fixture_dir" -type f -delete
    find "$fixture_dir" -depth -type d -empty -delete
}
trap cleanup EXIT

credential_file="$fixture_dir/migration.env"
cat >"$credential_file" <<'EOF'
POSTGRES_USER=uwa_migration_login
POSTGRES_PW=disposable-test-value
POSTGRES_DB=db25
EOF
chmod 0600 "$credential_file"
"$repo_root/scripts/check_database_credential_file.sh" \
    --credential-file "$credential_file" \
    --expected-user uwa_migration_login \
    --expected-uid "$(id -u)" >/dev/null

chmod 0644 "$credential_file"
if "$repo_root/scripts/check_database_credential_file.sh" \
    --credential-file "$credential_file" \
    --expected-user uwa_migration_login \
    --expected-uid "$(id -u)" >/dev/null 2>&1; then
    printf 'Expected loose credential mode rejection\n' >&2
    exit 1
fi
chmod 0600 "$credential_file"
sed -i 's/uwa_migration_login/uwa_runtime_login/' "$credential_file"
if "$repo_root/scripts/check_database_credential_file.sh" \
    --credential-file "$credential_file" \
    --expected-user uwa_migration_login \
    --expected-uid "$(id -u)" >/dev/null 2>&1; then
    printf 'Expected wrong credential principal rejection\n' >&2
    exit 1
fi

lock_file="$fixture_dir/operations.lock"
install -m 0660 /dev/null "$lock_file"
if UWA_OPERATION_LOCK_FILE="$lock_file" \
    "$repo_root/scripts/require_operation_lock.sh" exclusive >/dev/null 2>&1; then
    printf 'Expected missing inherited lock rejection\n' >&2
    exit 1
fi
UWA_OPERATION_LOCK_FILE="$lock_file" \
    "$repo_root/scripts/with_operation_lock.sh" --lock-file "$lock_file" --mode exclusive -- \
    bash -c '
        scripts/require_operation_lock.sh exclusive >/dev/null
        descriptor="$UWA_OPERATION_LOCK_FD"
        eval "exec ${descriptor}>&-"
        if scripts/require_operation_lock.sh exclusive >/dev/null 2>&1; then
            exit 1
        fi
    '

fake_bin="$fixture_dir/bin"
mkdir -p "$fake_bin"
cat >"$fake_bin/python" <<'EOF'
#!/usr/bin/env sh
printf '%s\n' "$*" >>"$DB25_PYTHON_LOG"
EOF
chmod 0755 "$fake_bin/python"
DB25_PYTHON_LOG="$fixture_dir/python.log" PATH="$fake_bin:$PATH" \
    sh "$repo_root/server/entrypoint.prod.sh" true >/dev/null
grep -qx 'manage.py migrate --check --noinput' "$fixture_dir/python.log"
if grep 'manage.py migrate' "$fixture_dir/python.log" | grep -vq -- '--check'; then
    printf 'Production entrypoint executed a migration mutation\n' >&2
    exit 1
fi

PYTHONDONTWRITEBYTECODE=1 python3 "$repo_root/scripts/validate_deployment_serialization.py" >/dev/null
printf 'DB25 deployment shell contracts passed\n'
