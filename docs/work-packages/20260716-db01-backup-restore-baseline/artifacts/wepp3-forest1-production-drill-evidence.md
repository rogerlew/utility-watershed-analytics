# wepp3 to forest1 Production Drill Evidence

Evidence: **Ran**

Date: 2026-07-16 America/Los_Angeles

Repository revision: `7a7d8cc91e759f80033125a093592eaa76d15124`

## Authority and boundary

The operator explicitly authorized a bounded `wepp3` to `forest1` backup and
isolated restore drill. The drill permitted production database reads,
protected task staging, encrypted transport, encrypted snapshot publication,
an isolated `forest1` restore, and non-mutating health checks. It excluded
production database writes or restore, deployment, service changes or
restarts, repository initialization, retention/prune, and unrelated workloads.

## Source and preflight

- Source host and container: `wepp3`, `postgis`
- Database: `pg4django`, 27,791,576,211 bytes at backup start
- Postgres/PostGIS: 17.5 / 3.5.2
- Source image:
  `sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`
- Source volume:
  `be7d3b8f6a3b08f300d2d3c45554e088eacce531a781d95bdff2fc9e32e22d51`
- Source aggregates: 126 watersheds, 195,457 subcatchments, and 86,895
  channels
- Destination: existing encrypted restic repository under
  `forest1:/wc1/utility-watershed-analytics-db-backups`
- Destination preflight: 1.1 TB free, restic 0.16.4, protected credential and
  repository permissions, and no conflicting backup/restore service or target

The task copied only `backup_database.sh` and `database_inventory.sh` into a
mode-`0700` production task directory. Their SHA-256 values matched the
repository files before execution.

## Backup and transport

- Backup start/completion: `2026-07-17T05:07:29Z` / `2026-07-17T05:15:06Z`
- Logical dump duration: 256 seconds
- Complete source workflow duration: 457 seconds
- Backup-set size: 1,214,819,392 bytes
- Archive size: 1,214,758,044 bytes
- Archive SHA-256:
  `7de71d1458b12afa15a4b3f098a351aa975425fe6631131febd09ea7d19c6802`
- Source and destination staging: files `0600`, directories `0700`
- Archive verification: completion marker, all declared SHA-256 checksums,
  `pg_restore --list`, and full decode to `/dev/null` passed
- Authenticated SSH pull: all 14 regular files and 1,214,819,392 bytes
  transferred in 429 seconds; every checksum passed again on `forest1`

Direct source-side restic SFTP was not used. `wepp3` did not resolve the short
host name, a public endpoint presented a different host key, and the verified
`forest1` Tailscale endpoint did not accept the production user's key. The
operator used the existing authenticated `forest1`-to-`wepp3` SSH path to pull
the protected set, then published it locally. Transport was SSH-encrypted and
the retained repository snapshot is restic-encrypted; this manual fallback
does not establish a permanent production scheduler identity.

## Encrypted snapshot

- Snapshot ID:
  `d18a3f06085a8aed92fdc1b48949f6dea2578114de169b1dde1730f31213716b`
- Snapshot time: `2026-07-16T22:24:03.358312217-07:00`
- Tags: `uwa-database`, `scheduled`
- Logical size: 1,214,819,392 bytes
- Publication verification: repository metadata and 5% rotating-data check
  passed
- Independent query: exactly one matching snapshot existed and it was the
  third database snapshot

The snapshot host field is `forest1` because the authorized pull fallback ran
the publisher there. The backup's checked metadata identifies the source as
`wepp3`; the snapshot host field must not be treated as source identity.

## Isolated restore

- Exact PostGIS image: source image above, imported read-only to `forest1`
- Pinned smoke image:
  `sha256:4ef239173320f1a59edc2d37e62f0ceda5821af106377efe0df50a010e294250`
- Target: disposable container on an internal temporary Docker network with no
  published host port
- Achieved RTO: 387 seconds against the accepted 86,400-second maximum
- Database comparison: roles/memberships subset, extensions, migrations,
  sequences, schema, and every table fingerprint exact
- Django smoke: system check, database connectivity, list, representative
  watershed detail, subcatchment, and channel reads passed
- Restored aggregates: 126 watersheds, 195,457 subcatchments, and 86,895
  channels; representative run `aversive-forestry`

The restore runner removed its target, internal network, generated credentials,
and temporary decrypted restore tree.

## Production postcheck and cleanup

After the drill, `wepp3` retained the same database image, volume, container
start time, zero restart count, checkout revision, branch, and aggregate row
counts. The database remained healthy, the backup lock was available, both
public site roots returned HTTP 200, and the canonical watershed API returned
HTTP 200.

The exact production task directory, both plaintext staging copies, imported
PostGIS image, pinned smoke-image tag, and protective local tag were removed.
The pre-drill `forest1` `postgis/postgis:latest` image ID remained unchanged.
The encrypted snapshot remains retained. Sanitized local command results remain
under mode-`0700`
`/wc1/utility-watershed-analytics-db-backups/drills/20260716-2158`; its five
files are mode `0600`. No dump, globals file, environment file, password, or
raw repository data is stored in Git.

## Remaining DB01 gates

This drill proves representative manual off-host transport, encrypted snapshot
publication, non-empty production-shaped restore, exact comparison, application
smoke, and achieved RTO. It does not prove an installed production scheduler,
the permanent `wepp3` to `forest1` transport identity, scheduled failure/stale
notification on the production source, or reboot persistence. DB01 therefore
remained on hold after this drill. The later
[production scheduler evidence](wepp3-production-scheduler-evidence.md) closes
all of those gates except reboot persistence.
