# wepp3 DB01 Post-Reboot Evidence

Evidence: **Ran**

Date: 2026-07-17 America/Los_Angeles

Repository revision: `7a7d8cc91e759f80033125a093592eaa76d15124`

## Authority and boundary

The operator restarted `wepp3` after `apt update` and `apt upgrade`, then
authorized the documented DB01 post-reboot checks. When those checks found the
serving database and server stopped, the operator temporarily enabled
passwordless sudo for the bounded parser correction and recovery. The task did
not reboot again, restore or write production data, replace or recreate a
container, build or pull an image, change the database volume, prune anything,
or converge the legacy production runtime.

## Reboot and backup persistence

- New boot: `2026-07-17 04:02:36` America/Los_Angeles
- Kernel: `6.8.0-136-generic`
- Docker Engine / Compose after upgrade: 29.6.2 / v5.3.1
- User linger: enabled
- User manager: running with Docker group 998
- `uwa-db-backup.timer`: enabled and active
- `uwa-db-backup-freshness.timer`: enabled and active
- Failed backup user units: zero

The documented post-reboot freshness invocation passed at snapshot age 18,003
seconds against the 90,000-second threshold. A final freshness invocation after
serving recovery also passed. The expected encrypted snapshot remained
readable both from `wepp3` through the restricted SFTP identity and directly
from `forest1`:

- snapshot:
  `1db1e3a475748e86692a26f5da0127e23399a2a2833a715bd68fd11133592359`;
- time: `2026-07-16T23:12:18.97776238-07:00`;
- host: `wepp3`; and
- tags: `uwa-database`, `scheduled`.

These checks close the DB01 reboot-persistence gate.

## Serving-runtime deviation and recovery

Postgres performed a clean fast shutdown during the operator's reboot. Caddy
returned automatically, but the database and server did not. The enabled
legacy `utility-watershed-analytics.service` failed five rapid boot attempts
because upgraded Compose rejected `.env` line 38, which was exactly `//`.
Site roots still returned HTTP 200 through Caddy while the API returned 502.

The task changed only that exact invalid comment to `#`; file ownership
`brandon:brandon` and mode `0664` were preserved. `docker compose config
--quiet` then passed. A Compose dry run showed that starting the legacy unit
would pull pgAdmin, build client/server images, create development containers,
and recreate the existing server. The task stopped that path and did not start
the unit.

Instead, after freezing exact identities, the task started only the existing
stopped containers `postgis` and
`utility-watershed-analytics-server-1`. PostGIS became healthy on the same
image and volume. The existing server reported no migrations to apply and
completed its production startup. No dry-run container or image artifact was
created.

After verification, the operator ran plain `systemctl disable` without
`--now`. Because the installed definition was a linked unit, systemd removed
both its enablement link and `/etc/systemd/system` registration and now reports
the unit `not-found`; it did not invoke `ExecStop` or change the running
containers. The unsafe source remains at
`/workdir/utility-watershed-analytics/utility-watershed-analytics.service`,
SHA-256 `fdec8821c894f62027782cf6257d0887183fbf0b896292caba92b0cf12bfd3e9`,
as direct DB02 evidence. A canonical unit must be installed before another
reboot. DB01 claims only the separately installed backup profile's reboot
persistence.

## Final invariants

- Database: `pg4django`, 27,791,576,211 bytes
- Watersheds: 126
- Subcatchments: 195,457
- Channels: 86,895
- PostGIS image:
  `sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`
- PostGIS volume:
  `be7d3b8f6a3b08f300d2d3c45554e088eacce531a781d95bdff2fc9e32e22d51`
- Existing server image:
  `sha256:4c5678dabc84a6b55e03b6c30b3bd2b4b591877f1682163ef6fcd56145c16139`
- `https://firewisewatersheds.org/`: HTTP 200
- `https://unstable.wepp.cloud/`: HTTP 200
- `https://firewisewatersheds.org/api/watershed/`: HTTP 200,
  1,609,932 bytes
- Failed backup user units on both hosts: zero

The temporary `/etc/sudoers.d/99-roger-nopasswd` override was removed and its
password-required baseline restored. No plaintext backup staging or temporary
remote verification resource remains.
