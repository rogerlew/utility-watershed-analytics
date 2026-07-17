# wepp3 Production Backup Scheduler Evidence

Evidence: **Ran**

Date: 2026-07-16 America/Los_Angeles

Repository revision: `7a7d8cc91e759f80033125a093592eaa76d15124`

## Authority and boundary

The operator authorized every remaining DB01 backup task except the host
reboot, then asked for an explicit hold. This permitted a restricted permanent
backup transport, user-local backup-only installation, timer activation,
production backup reads, isolated freshness failure injection, an isolated
`forest1` restore, health checks, and cleanup. It excluded rebooting either
host, production database writes or restore, serving Compose changes,
retention/prune, and unrelated workloads.

## Production installation

Interactive root access was unavailable, so the reviewed backup profile was
installed under the lingering `roger` user instead of changing system units:

- immutable bundle:
  `/home/roger/.local/lib/utility-watershed-analytics-backup/7a7d8cc`;
- current symlink:
  `/home/roger/.local/lib/utility-watershed-analytics-backup/current`;
- protected configuration:
  `/home/roger/.config/utility-watershed-analytics`;
- protected state:
  `/home/roger/.local/state/utility-watershed-analytics/backup`;
- user units: `uwa-db-backup.service`, `uwa-db-backup.timer`,
  `uwa-db-backup-freshness.service`,
  `uwa-db-backup-freshness.timer`, and
  `uwa-db-backup-failure@.service`; and
- restic client: 0.16.4.

Configuration and state directories are mode `0700`; credentials, trust data,
the operation lock, and success state are mode `0600`. Deployed scripts and
units matched the reviewed files. Target-path `systemd-analyze --user verify`
passed. The final SFTP wrapper's local and installed SHA-256 is
`28d582e6bcd9f6019d84857443501c9cf0541ee8c14511584fc6155eb406b942`.

The lingering user manager initially lacked the current Docker supplementary
group and the first backup service invocation failed before creating staging
or a snapshot. Its `OnFailure` journal alert fired. Exiting only the user
manager refreshed its group context; the serving containers were not restarted
or changed. A transient Docker probe then passed.

## Restricted transport

`wepp3` uses a dedicated key for direct client-side encrypted restic SFTP to
`forest1` over Tailscale. The key fingerprint is
`SHA256:3o3f8nVkOtDwQRlVtRgVc/3nObXGNk2bK5iUEnvCNrA`. Its single
`authorized_keys` entry is source-address-restricted and forced to
`internal-sftp`. The pinned authoritative `forest1` ED25519 host fingerprint
is `SHA256:1RN4k/LM4iFGjia5rlWMeDMoHLr96K39OX5IxuidRJE`.

The destination is the existing encrypted repository at
`forest1:/wc1/utility-watershed-analytics-db-backups/repository`. Direct
restricted SFTP, read-only restic listing, scheduled publication, independent
backup-host listing, and the final wrapper query passed. No repository was
initialized or pruned.

## Scheduled backup and freshness

The installed backup ran from `2026-07-16T23:04:58-07:00` through
`2026-07-16T23:18:01-07:00` against production container `postgis`, database
`pg4django`:

- source database size: 27,791,576,211 bytes;
- archive size: 1,215,877,353 bytes;
- archive SHA-256:
  `ace89cf2c1550db677f734e49e6714c352d969da71cb2eae13de144a94ea2d4d`;
- logical backup-set size: 1,215,938,601 bytes; and
- dump duration: 243 seconds.

Source checksums and archive decode passed. Restic published snapshot
`1db1e3a475748e86692a26f5da0127e23399a2a2833a715bd68fd11133592359`
at `2026-07-16T23:12:18.97776238-07:00`, with host `wepp3` and tags
`uwa-database,scheduled`. The repository check passed and `forest1`
independently confirmed the snapshot.

Normal freshness passed against the 90,000-second threshold. A runtime-only
one-second threshold then failed as planned, invoked the installed failure
unit, and wrote the accepted `Utility Watershed Analytics backup failure on
wepp3` journal alert. No optional external webhook is configured. The override
was removed exactly, normal freshness passed again, and no failed user units
remain.

Both production user timers are enabled and active. At final inspection, the
next backup was `2026-07-17T20:07:01-07:00` and the next freshness check was
`2026-07-17T05:32:04-07:00`.

## Isolated restore

`forest1` retained the exact production PostGIS image as
`postgis/postgis:uwa-production-db01-20260716` without changing its existing
`postgis/postgis:latest`, and retained the pinned smoke image
`sha256:4ef239173320f1a59edc2d37e62f0ceda5821af106377efe0df50a010e294250`.
The protected restore profile requires a non-empty database.

The installed weekly restore service restored the newest scheduled snapshot
above. Checksums, globals, archive restore, schema, every table fingerprint,
and non-empty Django smoke passed. Achieved RTO was 376 seconds against the
accepted 86,400-second maximum. The disposable target, internal network,
temporary credentials, and decrypted restore tree were removed.

The obsolete `forest1` development backup timer was disabled to prevent
development snapshots from mixing with production schedule evidence. Its
weekly retention and restore-test timers remain enabled and active.

## Production postcheck and cleanup

The `wepp3` boot time remained `2025-09-13 08:47:14`; no reboot occurred.
Production PostGIS remained healthy on the same image, volume, and start time
with zero restarts. The server and Caddy containers remained running. Database
aggregates remained 126 watersheds, 195,457 subcatchments, and 86,895 channels.
The production checkout identity and public site/API health remained
unchanged. Both hosts reported no failed user units.

Production plaintext staging was removed under the operation lock and is
empty. No dump, globals file, environment file, password, private key, or raw
repository data is stored in Git.

## Reboot completion

Permanent transport, installed scheduling, successful publication, normal and
stale freshness paths, journal notification, exact isolated restore, cleanup,
and no-reboot production health all passed. The operator later rebooted
`wepp3`; both timers persisted and post-reboot freshness plus independent
snapshot visibility passed. The serving-runtime deviation discovered during
that check is recorded separately and assigned to DB02. See the
[post-reboot evidence](wepp3-post-reboot-evidence.md).
