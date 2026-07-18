# DB16 — Attempt-scoped staging and recovery schema

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB16`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-17. Authority covers repository changes and isolated forest1 PostGIS,
container, migration, capacity, bounded-load, crash/expiry, cleanup-failure,
retry, and rollback tests.

## Objective

Add the smallest durable staging and recovery layer needed before a reconciler:
fixed logged attempt-scoped tables for watershed, subcatchment, channel, and
capability targets; explicit capacity accounting; bounded chunk loading with
heartbeats; and retryable cleanup for every expired non-terminal attempt while
leaving active serving and ledger history untouched.

## Scope

Included:

- one `DataReleaseStagingState` per attempt recording artifact, table, index,
  backup, WAL, and explicit-margin bytes, observed available bytes, lifecycle,
  row counts, cleanup attempts, retention, and sanitized cleanup error;
- four migration-created logged staging models keyed by DB15 attempt and run
  state, with canonical logical/run/child identities, source fingerprints,
  normalized geometry/payload or capability serving fields, validation state,
  uniqueness constraints, and attempt/identity indexes;
- bounded iterator-to-`bulk_create` loading with configurable batch ceiling,
  per-row model validation, per-batch transactions, and attempt heartbeat;
- fail-closed capacity preflight before any stage row is written;
- recovery that terminalizes expired `planning`, `staging`, and `applying`
  attempts in a separate transaction, observes diagnostic retention, and
  deletes only their staging rows;
- retryable cleanup after a simulated deletion failure, with bounded sanitized
  error persistence and retained attempt/release history;
- model, migration, integration, scale, and active-serving preservation tests;
  authoritative docs, roadmap, catalog, package, and sanitized evidence; and
- isolated production-image and PostGIS validation on forest1.

Excluded:

- production or `wepp3` access or mutation;
- release preparation/source adapters, real artifact fetches, reconciliation,
  activation, removal authorization, backup execution, rollback command, API,
  workflow dispatch, or management-command wiring;
- production capacity assertions, real release data/membership, credentials,
  cloud/provider infrastructure, paid services, or `/wc1` production writes;
  and
- commit, push, or pull request.

## Authority and inputs

- DB14 constraints/ownership: `docs/database-domain-integrity-contract.md`.
- DB15 ledger/lease contract: `docs/database-release-ledger-contract.md`.
- Architecture: `docs/database-deployment-architecture.md` sections 14.4, 16,
  and 17.3.
- Starting revision: `17c0626dc7d8d8ca8cbd737861086bb75a7f5202`.

## Decisions

- Staging tables are normal logged PostgreSQL tables. DB16 creates no dynamic
  DDL, unlogged table, shadow schema, or activation-time table.
- DB15 remains the sole attempt/lease authority. Staging rows reference its
  attempt and immutable target run state; DB16 does not add a second lease.
- The four staging tables make business identities, geometry, fingerprints,
  and capability references typed columns. Version-1 metadata and denormalized
  child attributes use normalized JSON payloads because activation mapping is
  owned by the later reconciler; secret-bearing keys remain prohibited.
- Each chunk is validated and committed independently. A process crash may
  leave complete logged chunks for diagnosis; no partial chunk is accepted.
- Capacity is one explicit sum: artifact + staging + indexes + verified backup
  + WAL + margin. Insufficient capacity records `SPACE_REJECTED`, fails the
  attempt, and writes no staging rows.
- Expiry never grants takeover. Recovery first marks the DB15 attempt failed,
  then cleans only that attempt's staging rows after `retention_until`.
- Cleanup state is retained for audit. A failed deletion records a sanitized
  error and remains `CLEANUP_PENDING`; a later retry uses the same allowlist.
- Serving watershed tables, active release pointer, release/run/artifact/
  capability history, auth, session, and other persistent tables are never
  cleanup targets.

## Plan

1. Add staging state and four tables.
2. Implement capacity and chunk loading.
3. Implement expiry recovery and cleanup retry.
4. Add migration and integration failure tests.
5. Rehearse scale and reconcile documentation.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch: `agent/database-backup-deployment-spec`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository and isolated Docker/PostGIS on forest1
- Mutation boundary: DB16 code, migrations, tests, documentation, and
  disposable test databases/containers/files
- Production server and production database: not authorized

## Gates

- Django migration graph and `makemigrations --check` pass.
- Migration creates five fixed logged tables with exact constraints/indexes and
  reverses without changing existing serving/ledger rows.
- Capacity tests cover every named component, exact-fit pass, and one-byte-short
  failure before staging writes.
- Bounded generator proof never materializes more than the configured batch;
  invalid or duplicate rows reject without a partial current batch.
- Concurrent attempt rejection and expired planning/staging/applying recovery
  pass using DB15's lease authority.
- Simulated crash leaves committed diagnostic chunks; retention defers cleanup;
  simulated cleanup failure records pending state; retry removes only staging.
- Active serving rows, singleton pointer, release history, capabilities, auth,
  and sessions are unchanged across recovery.
- Production server image build, Ruff, focused/full Django tests, docs/secret/
  whitespace checks, and `git diff --check` pass.

Skipped:

- production capacity, migration, recovery, or data mutation: separate
  production authority and later deployment packages are required;
- reconciler/activation behavior: DB20 and successor packages own it;
- client suite: no client behavior changes.

## Exit criteria

`EXECUTED-COMPLETE` requires all five models and constraints, bounded loading,
complete capacity accounting, every non-terminal expiry path, retention,
cleanup failure/retry, active-serving preservation, scale/reverse rehearsal,
full server gates, authoritative documentation, catalog, roadmap, and evidence.

Legitimate hold outcomes:

- `EXECUTED-HOLD-SCHEMA`: fixed tables cannot retain the version-1 normalized
  target needed for plan recomputation;
- `EXECUTED-HOLD-BOUNDS`: loading materializes unbounded rows or partial chunks;
- `EXECUTED-HOLD-RECOVERY`: an expired attempt cannot be terminalized and
  cleaned without touching active state; or
- `EXECUTED-HOLD-MIGRATION`: forward/reverse migration changes existing data.

## Artifacts

- `artifacts/db16-validation-evidence.md`

## Execution record

- Added one staging-state model and four fixed logged target models in migration
  `0010`, with attempt/run identity constraints and supporting indexes.
- Implemented exact capacity preflight, bounded transactional chunk loading,
  lease heartbeat, expiry terminalization, diagnostic retention, allowlisted
  cleanup, sanitized failure persistence, and retry.
- Passed 11 focused staging/migration tests and all 160 Django tests.
- Passed isolated synthetic production-shape forward/reverse rehearsal with 126
  watersheds, 195,457 subcatchments, and 86,895 channels; existing domain rows
  and the `EMPTY` singleton were unchanged.
- Built and validated production-server image
  `sha256:cbb52a979a1fda4c72ac745a6d33d085f75bb4c8c35cdf7dc6868549b5406619`.
- Did not access `wepp3`, production data, credentials, or production paths.
- Did not commit, push, or open a pull request for DB16, matching this package's
  recorded execution authority.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or production row data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match recorded authority.
