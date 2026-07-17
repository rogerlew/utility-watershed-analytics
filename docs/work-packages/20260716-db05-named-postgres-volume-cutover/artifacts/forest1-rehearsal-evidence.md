# DB05 `forest1` Named-Volume Rehearsal Evidence

Evidence mode: Ran unless marked Static

Date: 2026-07-17

## Boundary

The rehearsal ran only on development host `forest1` from repository commit
`6f46aaf643374047e2b5251fd5c15167c9843c0e`. It did not access `wepp3`, invoke
a GitHub workflow or runner, reboot a host, or mutate production. All database
containers used internal Docker networks and had no published ports.

The production-shaped source was encrypted snapshot
`4361efe3befe74d24922cbd0b950790c0e87cc036c9be482f76177a0f60893a8`
with exact source image
`sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`.
The accepted maximum RTO was 86,400 seconds. Preflight found 345,098,268,672
bytes available on the root filesystem and 1,156,727,046,144 bytes on the
rehearsal filesystem.

## Successful run

- Exact source restore into anonymous volume: 338 seconds; PostgreSQL 17.5,
  PostGIS 3.5.2, roles/memberships subset, extensions, migrations, sequences,
  schema, and all table fingerprints passed.
- Maintenance/quiescence: HTTP 503 and zero-writer observation passed.
- Encrypted pre-cutover snapshot:
  `709abac740c1ca710ad924ab259182e23f335e0305303c6565557cc63c425143`.
- Named-target restore: 358 seconds.
- Cutover: 370 seconds; actual rollback to the held anonymous source: 5
  seconds; reapply of the named target: 4 seconds.
- Named-volume persistence: container restart and container recreation passed.
- Pre/post table fingerprints: exact.
- Encrypted post-cutover snapshot:
  `d90d213ece0670fe87155c117402a70a517d3d3190303f3fd2fbb6ff91804025`.
- Independent post-cutover restore: 385 seconds; exact database comparison and
  production-mode Django/API smoke passed with 126 watersheds, 195,457
  subcatchments, and 86,895 channels.
- Total rehearsal duration: 2,195 seconds, within the accepted RTO.

## Fail-closed deviations

Four earlier passes stopped safely and informed the final harness:

1. Docker represented absent port bindings as an empty object rather than
   JSON null; the check now requires empty `docker port` output.
2. `restore_smoke` emits a Django system-check line followed by JSON; the
   parser now validates the final JSON line and required fields.
3. A restored target can contain a different database than its bootstrap
   environment; the backup helper now accepts explicit database and local-user
   overrides while preserving production defaults.
4. Test-mode Silk recorded smoke requests; restore smoke now uses the real
   production environment contract, where Silk is disabled.

Every stopped attempt removed its task containers, networks, volumes, and
plaintext staging before retry. The successful run also removed all disposable
resources. The ordinary development Compose services remained running and
healthy.

## Retained evidence

The successful mode-`0700` encrypted repository and sanitized result files are
retained at:

`/wc1/utility-watershed-analytics-db-backups/rehearsals/20260717-1127-db05-retry4`

Its retained size was 1.2 GiB at closeout. Credentials and database payloads
are not committed. The administrative command log is
`docs/sys-administration/logs/20260717-1127-db05-named-volume-rehearsal.md` and
is intentionally excluded from Git.

## Disposition

The rehearsal gates pass. This evidence does not authorize or claim a
production cutover, production reboot, or production post-cutover backup. DB05
is held for explicit production authority and a fresh read-only `wepp3`
identity/capacity/health freeze.
