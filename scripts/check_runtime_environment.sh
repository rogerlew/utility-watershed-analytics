#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

environment_file=""
expected_uid="0"

usage() {
    cat <<EOF
Usage: $(basename "$0") --env-file PATH [--expected-uid UID]

Validate the minimized production runtime environment without printing values.
EOF
}

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

while (($# > 0)); do
    case "$1" in
        --env-file)
            (($# >= 2)) || die "--env-file requires a value"
            environment_file="$2"
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

[[ -n "$environment_file" ]] || die "--env-file is required"
[[ "$expected_uid" =~ ^[0-9]+$ ]] || die "--expected-uid must be numeric"
for required_command in awk basename grep sort stat tr; do
    command -v "$required_command" >/dev/null 2>&1 \
        || die "Required command not found: $required_command"
done

[[ -f "$environment_file" && ! -L "$environment_file" ]] \
    || die "Runtime environment must be a regular non-symlink file"
[[ "$(stat --format '%a' "$environment_file")" == "600" ]] \
    || die "Runtime environment file must have mode 0600"
[[ "$(stat --format '%u' "$environment_file")" == "$expected_uid" ]] \
    || die "Runtime environment file has the wrong owner"
if grep -q $'\r' "$environment_file"; then
    die "Runtime environment file contains carriage returns"
fi

allowed_keys=(
    DJANGO_SECRET_KEY
    GUNICORN_KEEPALIVE
    GUNICORN_MAX_REQUESTS
    GUNICORN_MAX_REQUESTS_JITTER
    GUNICORN_THREADS
    GUNICORN_TIMEOUT
    GUNICORN_WORKERS
    POSTGIS_IMAGE
    POSTGRES_DB
    POSTGRES_PW
    POSTGRES_USER
    WEPPCLOUD_JWT_TOKEN
    WEPPCLOUD_JWT_TOKEN_2
)
required_keys=(
    DJANGO_SECRET_KEY
    POSTGIS_IMAGE
    POSTGRES_DB
    POSTGRES_PW
    POSTGRES_USER
    WEPPCLOUD_JWT_TOKEN
    WEPPCLOUD_JWT_TOKEN_2
)

declare -A seen=()
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" == *=* ]] || die "Runtime environment contains a malformed declaration"
    key="${line%%=*}"
    value="${line#*=}"
    [[ "$key" =~ ^[A-Z][A-Z0-9_]*$ ]] \
        || die "Runtime environment contains an invalid key"
    [[ -n "$value" ]] || die "Runtime environment contains an empty value: $key"
    [[ -z "${seen[$key]:-}" ]] || die "Runtime environment repeats a key: $key"
    seen[$key]=1
    allowed=0
    for allowed_key in "${allowed_keys[@]}"; do
        if [[ "$key" == "$allowed_key" ]]; then
            allowed=1
            break
        fi
    done
    ((allowed == 1)) || die "Runtime environment contains a non-runtime key: $key"
done <"$environment_file"

for required_key in "${required_keys[@]}"; do
    [[ -n "${seen[$required_key]:-}" ]] \
        || die "Runtime environment is missing a required key: $required_key"
done

postgis_image="$(awk -F= '$1 == "POSTGIS_IMAGE" {print substr($0, index($0, "=") + 1)}' "$environment_file")"
[[ "$postgis_image" =~ ^[^[:space:]@]+@sha256:[0-9a-f]{64}$ ]] \
    || die "POSTGIS_IMAGE must be pinned by repository digest"

printf 'Runtime environment contract passed: file=%s keys=%s\n' \
    "$(basename "$environment_file")" "${#seen[@]}"
