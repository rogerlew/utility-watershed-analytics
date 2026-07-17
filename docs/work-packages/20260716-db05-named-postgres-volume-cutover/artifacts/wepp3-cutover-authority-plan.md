# DB05 `wepp3` Production Authority Plan

Status: `EXECUTED-HOLD-PUBLISH`

Date: 2026-07-17

This bounded production proposal was explicitly authorized and executed on
2026-07-17. All operational checkpoints passed. Commit/push remained excluded,
so final repository publication is held separately.

## Requested authority

Authorize Codex, operating as `roger`, to access production host `wepp3` and,
only while holding the canonical exclusive operations lock:

1. refresh read-only identities, capacity, runtime health, timers, and backup
   repository access;
2. enter reviewed HTTP 503 maintenance and stop application writers;
3. create and verify a fresh encrypted off-host backup;
4. create `utility-watershed-analytics_postgres_data`, restore and verify it
   with the unchanged pinned PostGIS image, and switch the canonical runtime;
5. exercise actual rollback to the held anonymous source, reapply the named
   target, and verify restart persistence;
6. install the final reviewed Compose/systemd convergence, reboot `wepp3`, and
   verify boot persistence; and
7. create and isolated-restore-test a post-cutover encrypted backup, then leave
   the anonymous source retained and prune-prohibited for DB05A.

This authority does not include a PostgreSQL/PostGIS upgrade, data reload,
watershed release change, source-volume deletion, backup pruning, unrelated
host changes, GitHub dispatch, commit, or push.

## Historical identity assertions

The last authorized DB03 production evidence recorded:

- database container
  `d2f0c406fc2bf02d5461b88d6f803112da1c9933494c2c6a68bf829268898bf2`;
- image
  `sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`;
- anonymous source volume
  `be7d3b8f6a3b08f300d2d3c45554e088eacce531a781d95bdff2fc9e32e22d51`;
- project/service `utility-watershed-analytics` / `db`; and
- mount destination `/var/lib/postgresql/data`.

These are comparison inputs, not current facts. The first production action is
a read-only refresh. Any mismatch stops the package before maintenance or
mutation and is reported to `roger`.

## Mandatory preflight

Before maintenance, record and require:

- host is exactly `wepp3`; branch/commit and working tree are accepted;
- database container, image, anonymous volume, mount, project, health, start
  time, and restart count match the refreshed freeze;
- final rendered target resolves locally to the same image and named volume,
  with no database upgrade or host-published port;
- the production database and public API are healthy;
- backup/freshness/restore timers are healthy and the off-host repository is
  reachable without printing credentials;
- root and Docker filesystems have enough capacity for source, named target,
  protected staging, and WAL margin;
- no deployment or database operation is active, and the exclusive lock can be
  acquired normally; and
- passwordless sudo, if temporarily granted, is validated and scheduled for
  removal at closeout.

The accepted maximum RTO is 86,400 seconds. Failure of any preflight is a hold,
not permission to improvise.

## Execution checkpoints

1. Preserve the exact source with a stopped holder container and
   prune-prohibition labels before detachment.
2. Route all public requests to the reviewed HTTP 503 maintenance response;
   prove it externally, then stop Django writers without `docker compose down`.
3. Prove bounded write quiescence with active-session and inventory checks.
4. Run the locked production backup path and verify completion, checksums,
   encrypted off-host snapshot ID, repository check, and freshness.
5. Restore that exact backup into the empty canonical named volume using the
   unchanged image. Compare roles, memberships, extensions, migrations,
   sequences, schema, every table fingerprint, and production-mode smoke.
6. Switch only through the reviewed Compose action. Reject unexpected create,
   pull, build, upgrade, unrelated service, network, or volume actions.
7. Verify internal and public application behavior, named-volume identity, and
   removal of PostgreSQL/Django host publication while maintenance remains on.
8. Actually switch back to the held anonymous source, verify health and data,
   then reapply the accepted named target and verify again.
9. Restart/recreate only as reviewed, install the final safe unit/Compose
   target, reboot, and verify named-volume identity and services after boot.
10. Remove maintenance only after acceptance, then run and isolated-restore-test
    a new encrypted backup within RTO.

## Rollback and stop conditions

Before the canonical target is accepted, rollback is the held anonymous source.
After reapply and reboot, rollback remains the same held source plus the fresh
pre-cutover encrypted snapshot. Do not delete either.

Stop immediately on identity drift, inability to prove quiescence, backup or
inventory failure, unexpected Compose action, incompatible version, smoke or
public-route failure, missed RTO, loss of the holder reference, or inability to
reacquire the exact source. Keep maintenance active, preserve both volumes,
record the state, and request a new decision from `roger`.

## Publication hold

Production execution is complete and reviewed commit `2c6f426...` is published
on the agent branch. The next action requires explicit fork `main`
fast-forward authority, followed by a clean fast-forward of the fork-owned
production checkout. No source-volume deletion is authorized; that remains
DB05A.
