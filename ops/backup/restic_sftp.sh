#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'
umask 077

restic_real_bin="${RESTIC_REAL_BIN:-$HOME/.local/bin/restic}"
identity_file="${BACKUP_SFTP_IDENTITY_FILE:-$HOME/.config/utility-watershed-analytics/backup-sftp-key}"
known_hosts_file="${BACKUP_SFTP_KNOWN_HOSTS_FILE:-$HOME/.config/utility-watershed-analytics/known_hosts}"

[[ -x "$restic_real_bin" ]] \
    || { printf 'ERROR: Restic executable is unavailable: %s\n' "$restic_real_bin" >&2; exit 1; }
[[ -r "$identity_file" ]] \
    || { printf 'ERROR: SFTP identity is unavailable: %s\n' "$identity_file" >&2; exit 1; }
[[ -r "$known_hosts_file" ]] \
    || { printf 'ERROR: SFTP known-hosts file is unavailable: %s\n' "$known_hosts_file" >&2; exit 1; }
[[ "$identity_file" != *[[:space:]]* && "$known_hosts_file" != *[[:space:]]* ]] \
    || { printf 'ERROR: SFTP paths must not contain whitespace\n' >&2; exit 1; }

sftp_arguments="-i $identity_file -o UserKnownHostsFile=$known_hosts_file -o StrictHostKeyChecking=yes -o BatchMode=yes -o IdentitiesOnly=yes"

exec "$restic_real_bin" -o "sftp.args=$sftp_arguments" "$@"
