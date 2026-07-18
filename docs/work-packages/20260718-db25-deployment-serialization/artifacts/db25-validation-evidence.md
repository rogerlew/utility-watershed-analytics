# DB25 validation evidence

Date: 2026-07-18

Environment: `forest1`, repository
`/workdir/utility-watershed-analytics`, branch
`agent/database-backup-deployment-spec`, starting revision
`92ce360` (`Complete DB24 reconciler resilience`).

Evidence mode: Mixed. Commands are Ran; workflow/contract/scope review is
Static.

## Final image and tests

The production server image for the exact DB25 server code built locally as:

```text
sha256:2e355618f60d3d7b4107a52de1599ce49f26fb38cad2819601d9213b5b46efcf
```

This is a local forest1 image ID, not a published image or production
deployment authority.

Final exact-image proof:

```text
All checks passed!
No changes detected

Found 206 test(s).
Ran 206 tests in 90.655s
OK (skipped=1)
```

The one full-suite skip is the DB09 repository-schema integration inside the
production server image, which intentionally contains only `server/`. The DB08
validator plus 7 tests and DB09 validator plus 12 tests passed against the exact
image with the repository mounted. Five focused DB25 tests passed in 0.849
seconds; the combined DB20–DB25 regression passed 27 tests in 37.102 seconds
with the same expected DB09 skip.

## Serialization and startup proof

Static workflow validation found one current production workflow and the one
accepted concurrency group, `utility-watershed-analytics-production`, with
cancellation disabled. The validator also confirmed explicit separately
credentialed migration, pre-worker application compatibility, and absence of
startup migration mutation.

Real host-process tests covered exclusive contention, concurrent shared locks,
shared-to-exclusive rejection, cancellation and reacquisition, nested locks,
wrong/stale descriptors, and a deliberately closed inherited descriptor.
Application deploy mocks reasserted the lock at mutation boundaries, passed the
migration file via Compose `--env-from-file`, invoked exactly one migration,
ran compatibility, and preserved database identity. A separate real Compose
probe confirmed the migration file overrides the runtime database variables in
the one-shot container.

The exact production image started against disposable PostGIS as
`uwa_runtime_login`. It ran `migrate --check --noinput`, completed Django deploy
checks, and handed off without applying a migration. Fourteen pre-existing
Django/schema/security warnings were warnings rather than failures and were not
changed by DB25.

## Compatibility proof

Synthetic EMPTY-base attempts proved the successful application and staged
release paths. Wrong materializer image, materializer Git, application Git,
expected base, target plan coordinates, and an incompatible active migration
failed before activation. Missing core artifact roles and missing expected
capability staging also failed before activation. Management command output was
bounded JSON and missing/non-ordinary plans failed closed.

## Role and rotation proof

The role contract was applied twice to fully migrated disposable PostGIS,
proving convergence. Seven NOLOGIN privilege roles and seven LOGIN principals
were provisioned without passwords, then every principal was rotated from a
first synthetic value to a second. Each first value authenticated before
rotation and failed afterward; each replacement authenticated.

Executed permission probes proved status, runtime, staging, activation,
backup, migration, and restore allowed only their documented boundaries.
Status/runtime/staging could not mutate serving state or the active pointer;
runtime could not read staging; status could not read non-watershed auth state
or assume activation; activation could not create schema; backup could not
write; migration could perform DDL; and restore had no inherited access before
explicit `SET ROLE`. Restore configuration forced full statement and duration
logging.

## Boundary review

- `wepp3` was not contacted.
- No production role, credential, migration, workflow, release, plan, pointer,
  database, service, or secret was inspected or changed.
- No credential values, `.env`, dumps, PII, real coordinates, or source data
  were recorded. All disposable password files were removed.
- DB25 was not committed, pushed, published, dispatched, or deployed during
  governed execution.
- Disposable DB25 PostGIS/network state was removed after acceptance; the
  validated local image was retained.
