#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

action=""
container="postgis"
identity_file=""

usage() {
    cat <<EOF
Usage:
  $(basename "$0") capture --output FILE [--container NAME]
  $(basename "$0") assert --expected FILE [--container NAME]

Capture or assert the exact PostgreSQL container, image, Compose labels, and
data-volume identity. The report contains identifiers only, never environment
values or database contents.
EOF
}

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

(($# > 0)) || die "capture or assert is required"
action="$1"
shift
[[ "$action" == "capture" || "$action" == "assert" ]] \
    || die "Action must be capture or assert"

while (($# > 0)); do
    case "$1" in
        --container)
            (($# >= 2)) || die "--container requires a value"
            container="$2"
            shift 2
            ;;
        --output)
            (($# >= 2)) || die "--output requires a value"
            [[ "$action" == "capture" ]] || die "--output is valid only with capture"
            identity_file="$2"
            shift 2
            ;;
        --expected)
            (($# >= 2)) || die "--expected requires a value"
            [[ "$action" == "assert" ]] || die "--expected is valid only with assert"
            identity_file="$2"
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

[[ -n "$identity_file" ]] || die "An identity file is required"
[[ "$identity_file" != *$'\n'* ]] || die "Identity path must not contain a newline"
for required_command in cmp dirname docker mktemp mv python3 rm; do
    command -v "$required_command" >/dev/null 2>&1 \
        || die "Required command not found: $required_command"
done

capture_identity() {
    local output_path="$1"
    local inspect_path
    inspect_path="$(mktemp /tmp/uwa-database-inspect.XXXXXX)"
    trap 'rm -- "$inspect_path"' RETURN
    docker inspect "$container" >"$inspect_path" \
        || die "PostgreSQL container not found: $container"
    python3 - "$inspect_path" >"$output_path" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as inspect_stream:
    records = json.load(inspect_stream)
if len(records) != 1:
    raise SystemExit("expected exactly one database container")
record = records[0]
labels = record["Config"].get("Labels") or {}
data_mounts = [
    mount
    for mount in record.get("Mounts", [])
    if mount.get("Destination") == "/var/lib/postgresql/data"
]
if len(data_mounts) != 1:
    raise SystemExit("expected exactly one PostgreSQL data mount")
mount = data_mounts[0]
values = {
    "compose_config_hash": labels.get("com.docker.compose.config-hash", ""),
    "compose_project": labels.get("com.docker.compose.project", ""),
    "compose_service": labels.get("com.docker.compose.service", ""),
    "compose_working_dir": labels.get("com.docker.compose.project.working_dir", ""),
    "container_id": record["Id"],
    "container_name": record["Name"].removeprefix("/"),
    "data_destination": mount["Destination"],
    "data_driver": mount.get("Driver", ""),
    "data_mount_name": mount.get("Name", ""),
    "data_mount_source": mount["Source"],
    "data_mount_type": mount["Type"],
    "image_id": record["Image"],
    "image_reference": record["Config"]["Image"],
}
for key in sorted(values):
    value = values[key]
    if "\n" in value:
        raise SystemExit(f"identity value contains a newline: {key}")
    print(f"{key}={value}")
PY
    rm -- "$inspect_path"
    trap - RETURN
}

if [[ "$action" == "capture" ]]; then
    identity_parent="$(dirname -- "$identity_file")"
    [[ -d "$identity_parent" && -w "$identity_parent" ]] \
        || die "Identity output directory is unavailable: $identity_parent"
    identity_partial="$(mktemp "$identity_parent/.database-identity.XXXXXX")"
    capture_identity "$identity_partial"
    mv -- "$identity_partial" "$identity_file"
    printf 'Database identity captured: %s\n' "$identity_file"
    exit 0
fi

[[ -f "$identity_file" && -r "$identity_file" ]] \
    || die "Expected identity file is unavailable: $identity_file"
actual_file="$(mktemp /tmp/uwa-database-identity.XXXXXX)"
cleanup() {
    rm -- "$actual_file"
}
trap cleanup EXIT
capture_identity "$actual_file"
cmp --silent "$identity_file" "$actual_file" \
    || die "PostgreSQL container, image, project, or data-volume identity changed"
trap - EXIT
cleanup
printf 'Database identity unchanged\n'
