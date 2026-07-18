# DB27 validation evidence

Date: 2026-07-18

Environment: `forest1`, repository
`/workdir/utility-watershed-analytics`, branch
`agent/database-backup-deployment-spec`, starting revision `fde1d7b`
(`Complete DB26 database deployment orchestration`).

Evidence mode: Mixed. Repository tests, synthetic role/status rehearsal,
workflow/static validation, exact container build, and disposable PostGIS are
Ran. GitHub reviewer/environment enforcement and production runner/unit paths
are Static because external mutation and production access were not authorized.

## Authorization and workflow rehearsal

Eight focused tests passed in 2.073 seconds:

```text
Ran 8 tests
OK
```

Two independently prepared deploy bundles had the same authorization SHA-256.
A rollback bundle had a distinct fixed action and could pass only the rollback
verifier. The rehearsal rejected a wrong action/role, operation ID, source
commit, authorization digest, mutated file, writable file, symlink source,
source/request mismatch, secret-bearing document, and incomplete coordinates.
Bundle directories were mode `0700`; all members were mode `0400`; verification
reports were atomic mode `0600`.

Workflow mutation tests rejected a push-triggered data deploy, preparation on a
self-hosted runner, collapsed deploy/rollback environment, rollback action on
the deploy path, missing protected authorization hash, and DB26 invocation
from the merge-triggered application workflow. Static policy reported:

```json
{"deploy_environment":"production-data-deploy","merge_deploys_data":false,"prepare_environment":null,"production_concurrency_group":"utility-watershed-analytics-production","rollback_environment":"production-data-rollback","status":"passed"}
```

All workflow YAML parsed. The DB25 serialization validator recognized the
application, data-deploy, and data-rollback production environments under the
same non-cancelling concurrency group. The data-contract CI now runs DB27's
validators/tests when these paths change.

The workflows were not dispatched. No GitHub artifact or environment was
created. Required reviewers, deployment branch restrictions, runner sudo, and
repository variables remain a later authorized administrative task; tests do
not overstate those external settings as Ran.

## Active status and private monitoring

The public endpoint passed exact EMPTY and ACTIVE tests. ACTIVE returned the
release ID, manifest, data contract, activation time, and aggregate watershed,
subcatchment, channel, and capability counts from the ledger. Both responses
used `Cache-Control: no-store`. Response-content checks found no attempt,
failure, backup, credential, filesystem, or lease-owner details.

The private monitor passed the healthy fixture and failed each injected active
mismatch, inventory count mismatch, low capacity, excessive growth, stale
artifact, stale backup, retained failed attempt, and abandoned nonterminal
attempt. Malformed state, broad private modes, and secret-shaped input returned
a distinct invalid-input exit. Reports were atomic mode `0600` beneath a mode
`0700` directory.

## Exact image and server regression

The final production server image built as:

```text
sha256:1b6c0b59dbe7f7b31ea23a861e646e9b4717d9b6c1c338ce9654361e558b359f
```

Against disposable PostGIS pinned at
`sha256:4e8c30197f7ce4190cf11a1b8c44bea35a58507558cffa48570814beba77b099`:

```text
Found 208 test(s).
Ran 208 tests in 92.325s
OK (skipped=1)
All checks passed!
No changes detected
```

The expected skip is the established DB09 repository-schema integration; the
production server image intentionally contains only `server/`. Ruff covered
the final server tree. Migration drift was empty. A separate repository mount
Ruff pass covered all new DB27 Python scripts and tests.

## Boundary and cleanup

- `wepp3` was not contacted.
- No production data, request, plan, inventory, credential, backup, service,
  environment, runner setting, deployment, rollback, or database was read or
  changed.
- No GitHub workflow was dispatched and no artifact, environment, secret,
  variable, branch rule, commit, push, or PR was created during DB27 execution.
- Synthetic files contained no real coordinates, accounts, PII, or secrets.
- Disposable authorization bundles, status snapshots/reports, PostGIS
  containers, and Docker networks were removed. The final local server image
  was retained as validation evidence.
