#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'

credential_file=""
expected_uid="0"
expected_user=""

usage() {
    cat <<EOF
Usage: $(basename "$0") --credential-file PATH --expected-user USER [--expected-uid UID]

Validate one minimized PostgreSQL credential file without printing values.
EOF
}

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

while (($# > 0)); do
    case "$1" in
        --credential-file)
            (($# >= 2)) || die "--credential-file requires a value"
            credential_file="$2"
            shift 2
            ;;
        --expected-user)
            (($# >= 2)) || die "--expected-user requires a value"
            expected_user="$2"
            shift 2
            ;;
        --expected-uid)
            (($# >= 2)) || die "--expected-uid requires a value"
            expected_uid="$2"
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

[[ -n "$credential_file" ]] || die "--credential-file is required"
[[ "$expected_uid" =~ ^[0-9]+$ ]] || die "--expected-uid must be numeric"
[[ "$expected_user" =~ ^uwa_[a-z]+_login$ ]] || die "Expected database user is invalid"
[[ -f "$credential_file" && ! -L "$credential_file" ]] \
    || die "Credential file must be a regular non-symlink file"
[[ "$(stat --format '%a' "$credential_file")" == "600" ]] \
    || die "Credential file must have mode 0600"
[[ "$(stat --format '%u' "$credential_file")" == "$expected_uid" ]] \
    || die "Credential file has the wrong owner"
grep -q $'\r' "$credential_file" && die "Credential file contains carriage returns"

declare -A values=()
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" == *=* ]] || die "Credential file contains a malformed declaration"
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
        POSTGRES_USER|POSTGRES_PW|POSTGRES_DB) ;;
        *) die "Credential file contains an unexpected key: $key" ;;
    esac
    [[ -z "${values[$key]+present}" ]] || die "Credential file repeats a key: $key"
    [[ -n "$value" ]] || die "Credential file contains an empty value: $key"
    [[ "$value" != *$'\n'* ]] || die "Credential value contains a newline"
    values[$key]="$value"
done <"$credential_file"

for key in POSTGRES_USER POSTGRES_PW POSTGRES_DB; do
    [[ -n "${values[$key]+present}" ]] || die "Credential file is missing: $key"
done
[[ "${values[POSTGRES_USER]}" == "$expected_user" ]] \
    || die "Credential file names the wrong database principal"

printf 'Database credential contract passed: file=%s user=%s\n' \
    "$(basename "$credential_file")" "$expected_user"
