# DB05 `wepp3` Production Named-Volume Cutover Evidence

Evidence mode: Ran unless marked Static

Date: 2026-07-17

## Authority and frozen source

`roger` explicitly authorized the reviewed production plan and enabled
temporary passwordless sudo. Fresh preflight matched the DB03 source:

- container `d2f0c406fc2bf02d5461b88d6f803112da1c9933494c2c6a68bf829268898bf2`;
- image `sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`;
- anonymous volume
  `be7d3b8f6a3b08f300d2d3c45554e088eacce531a781d95bdff2fc9e32e22d51`;
- PostgreSQL 17.5 and PostGIS 3.5.2;
- healthy, zero restarts, zero active writers; and
- 622,786,355,200 bytes available on the Docker filesystem.

Unit/timers, fork runner, public routes, exact lock availability, and
passwordless sudo passed. The historical upstream checkout and intentional
untracked `compose.db03.yml` matched DB03 evidence rather than database drift.

## Maintenance, backup, and target restore

The exclusive host lock covered maintenance through accepted cutover. Both
public domains and representative API returned HTTPS 503 externally before
Django stopped. A bounded inventory interval proved zero writers and exact
extensions, migrations, sequences, and table fingerprints.

Fresh pre-cutover backup:

- archive: 1,212,820,636 bytes;
- SHA-256: `47e0f0b29c8e9fc95f02f864a577b61e01043b18107e8318851755c94769ef55`;
- encrypted snapshot:
  `cc7236b38c3d6cdf1b2cce8307a57e951e142ae92e545808c318dfd0763062dd`;
- off-host repository verification: passed.

The exact backup restored into empty named volume
`utility-watershed-analytics_postgres_data` in 388 seconds. Roles/memberships
subset, extensions, migrations, sequences, schema, and every table fingerprint
matched.

The historical serving image predates `restore_smoke`, so the fail-closed
harness stopped after exact database comparison and before source/checkout
mutation. The exact rehearsal-tested smoke image `sha256:3c58c34...` was
streamed from `forest1`, verified, and used only for production-mode restored
API checks. Maintenance, source, and target remained protected throughout.

## Cutover and rollback

- named cutover: 4 seconds;
- actual rollback to the held anonymous source: 6 seconds;
- named-target reapply: 5 seconds;
- database restart persistence: passed;
- Compose container recreation persistence: passed;
- final inventory: exact;
- normal public API recovery: HTTP 200.

Final database container
`f315e224ab5704d4610c32cef88544b44073c9dcc38a8de5d2ebc22c8a5cd2d8`
uses the unchanged exact image and named volume with no host-published port.
The stopped `uwa-db05-source-holder` references the exact anonymous source and
has `com.utility-watershed-analytics.prune=prohibited`. Neither source nor
target is authorized for deletion.

## Runtime, reboot, and sockets

The protected database identity, immutable DB05 runtime bundle, safe systemd
unit, and final Compose target were installed. The canonical checkout is owned
by `roger`, on fork `main` commit
`6f46aaf643374047e2b5251fd5c15167c9843c0e`, with the upstream retained as a
secondary remote.

The unit restart preserved exact container/volume identity. Reboot changed boot
ID from `f9aefdca-a87f-4385-abd9-598599d370ea` to
`b9c543e3-6c30-4b62-8993-f033b43b6076`. The enabled unit completed after
acquiring the boot-time operations lock. Database, server, Caddy, backup and
freshness timers, fork runner, public routes, and lock reacquisition passed.
Host ports 5432 and 8000 have no listeners; Caddy alone publishes 80/443.

## Post-cutover recovery

Post-cutover backup:

- archive: 1,212,259,187 bytes;
- SHA-256: `da89c44f2a7755ecfab119c918443d0446d652123b392a6273a4c1a9b5d93408`;
- encrypted snapshot:
  `cb9284c0db7c0e414d2de6852472df04f67a724aab527e37c43ac56a55335004`.

`forest1` selected that snapshot by global timestamp, restored it into an
internal disposable target, and passed exact schema/table comparison plus
production-mode API smoke in 386 seconds against the accepted 86,400-second
maximum RTO. The smoke reported 126 watersheds, 195,457 subcatchments, and
86,895 channels. Disposable restore resources were removed.

## Closeout

- Production task/evidence/runtime directories are mode `0700`.
- No task plaintext `.env`, maintenance container, temporary target/source
  container, or target network remains.
- The database is healthy with zero restarts; exact identity assertion passes.
- Public root and representative APIs return 200.
- Temporary passwordless sudo was removed and no longer passes `sudo -n`.
- Separate publication authority first published the reviewed DB05 history to
  fork `main` at `d52aae4...`, then reconciled the production checkout under
  the exclusive operations lock without restarting a service.
- The obsolete untracked `compose.db03.yml` was checksummed as
  `ee2ef4d0...`, preserved mode `0600` in the protected DB05 evidence
  directory, and removed only from the checkout. The tracked production
  Compose SHA remained `78e05749...` across the fast-forward.
- Independent verification found the checkout clean, exact database container
  `f315e224...` healthy with zero restarts on the named volume, the anonymous
  source held and prune-prohibited, unit/timers/runner active, no 5432/8000
  listeners, and all four canonical root/API checks returning HTTP 200.

Detailed administrative logging is retained outside Git at
`docs/sys-administration/logs/20260717-1322-db05-wepp3-production-cutover.md`.
