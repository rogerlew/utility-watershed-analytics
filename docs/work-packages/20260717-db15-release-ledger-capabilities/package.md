# DB15 — Release ledger and capability-serving schema

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB15`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-17. Authority covers repository changes and isolated forest1 PostGIS,
container, migration, transition, lease, activation, failure-fixture, and
rollback tests.

## Objective

Add the small durable database ledger required by the accepted release
contracts: immutable release coordinates and history, one lockable active
pointer initialized to `EMPTY`, attributable deployment attempts with bounded
leases and sanitized failures, per-run fingerprints and artifact lineage, and
capability rows whose serving visibility follows the active release atomically.

## Scope

Included:

- `DataRelease` with version-1 manifest, fingerprint, materializer, count,
  validation, predecessor, and lifecycle coordinates;
- singleton `ActiveDataRelease`, created by migration in coherent `EMPTY`
  state and later transitioned to coherent `ACTIVE` state;
- `DataReleaseAttempt` with operator/workflow attribution, reviewed/actual plan
  hashes, timestamps, lease owner/heartbeat/expiry, backup/report references,
  and sanitized failure phase/summary;
- `DataRunState` with stable logical identity, source revision, version-1 run,
  domain-input and optional capability fingerprints, actual counts, and
  validation status;
- per-run immutable artifact lineage and `RunCapability` serving configuration
  with durable HTTPS base/index references and immutable index checksum;
- a transaction helper that locks the singleton, reasserts the expected base,
  validates release/run/capability consistency, updates release and attempt
  states, and changes active capability visibility in the same transaction;
- database/model constraints, migration bootstrap/reverse tests, state/lease/
  sanitization tests, authoritative docs, roadmap, catalog, and evidence; and
- isolated production-image and PostGIS validation on forest1.

Excluded:

- production or `wepp3` access or mutation;
- staging tables, reconciler writes, artifact fetching, plan generation,
  backup execution, API endpoints, workflow dispatch, or release activation;
- real release manifests, production memberships, credentials, raw user data,
  cloud/provider infrastructure, or new paid services; and
- DB13 logical-link contraction, commit, push, or pull request.

## Authority and inputs

- DB08 contract: `docs/database-release-schema-contract.md`.
- DB09 contract: `docs/database-fingerprint-plan-contract.md`.
- DB13 identity shape: `docs/database-watershed-identity-migration.md`.
- DB14 ownership boundary: `docs/database-domain-integrity-contract.md`.
- Architecture: `docs/database-deployment-architecture.md` sections 9, 14,
  17, and 18.
- Starting revision: `06cb3153f47ede052a8dc3ca06716bbd817a5592`.

## Decisions

- Release payload coordinates are immutable after insertion. Lifecycle status
  changes only through the bounded activation helper.
- Supported schema, data, identity, artifact, and fingerprint contract versions
  are exactly version 1; incompatible rows fail closed.
- Attempt lease fields live on the attempt, matching the accepted architecture.
  At most one lease is active. Expiry is observable but does not silently grant
  takeover; DB16 recovery terminalizes it first.
- Attempt attribution is either `operator` or `workflow`. No application user
  or PII model is introduced.
- Failure summaries are single-line, length-bounded, and redact common secret
  assignments and URI user information before persistence.
- Run and capability history remains release-scoped. Runtime visibility is a
  query against the singleton active release, so staging a successor never
  advertises its capabilities early.
- DB15 supports the accepted RHESSys capability type and its three modes. A new
  capability family requires a contract change rather than an unconstrained
  string.
- Artifact and serving URIs remain durable HTTPS references from DB08. The
  operator-owned `forest1:/wc1` tree remains the separate content-addressed
  backup/cache implementation selected by DB10–DB12.

## Plan

1. Add ledger and capability models/migration.
2. Implement state, lease, and activation helpers.
3. Add constraint, migration, and lifecycle tests.
4. Rehearse forward/reverse isolated migration.
5. Reconcile authoritative docs and evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch: `agent/database-backup-deployment-spec`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository and isolated Docker/PostGIS on forest1
- Mutation boundary: DB15 code, migrations, tests, documentation, and
  disposable test databases/containers
- Production server and production database: not authorized

## Gates

- Django migration graph and `makemigrations --check` pass.
- Migration creates exactly one coherent `EMPTY` singleton and reverses cleanly.
- Unsupported versions, invalid hashes/URIs/statuses, duplicate release/run/
  capability identities, and competing active leases fail.
- Tests cover first activation, successor activation, retained history,
  rollback reactivation, legal/illegal attempt transitions, expiry without
  silent takeover, sanitized failure summaries, and operator/workflow identity.
- Staged capability rows remain invisible; activation makes exactly the target
  release visible in the singleton update transaction.
- Production server image build, Ruff, focused/full Django tests, docs/secret/
  whitespace checks, and `git diff --check` pass.

Skipped:

- production migration/activation: requires separate production schema, data,
  backup, maintenance, and application mutation authority;
- reconciler/staging and recovery execution: owned by DB16 and later packages;
- client suite: no client behavior changes.

## Exit criteria

`EXECUTED-COMPLETE` requires all schema records and constraints, singleton
bootstrap, bounded helpers, required positive/negative lifecycle proof, full
server gates, authoritative documentation, catalog, roadmap, and sanitized
evidence.

Legitimate hold outcomes:

- `EXECUTED-HOLD-CONTRACT`: DB08/DB09 coordinates cannot map without inventing
  a new contract decision;
- `EXECUTED-HOLD-ATOMICITY`: active release and capability visibility cannot be
  changed in one database transaction; or
- `EXECUTED-HOLD-MIGRATION`: singleton bootstrap or reverse migration is not
  clean on isolated PostGIS.

## Artifacts

- `artifacts/db15-validation-evidence.md`

## Execution record

Implemented migration `0009_release_ledger_capabilities`, six matching models,
database/model constraints, helper-gated lifecycle writes, bounded attempt and
lease transitions, secret-safe failure summaries, exact base/plan activation,
and active-pointer capability visibility.

The focused ledger/migration suite passed 11 tests. A synthetic
production-shaped isolated rehearsal passed with 126 watersheds, 195,457
subcatchments, and 86,895 channels; forward migration took 0.242 seconds,
reverse took 0.284 seconds, and all serving counts and sampled child IDs were
unchanged. First activation, successor history, rollback reactivation,
operator/workflow attribution, active and expired lease conflict, invalid state
transitions, incompatible version, sanitized failure, and capability mismatch
fixtures passed.

The final production image is
`sha256:f4cdbd004811c30961d8fee2e9393e0b10a44c468a1befc3a49fc2a6f196b966`.
Ruff, migration drift checking, all 149 server tests, Python syntax,
documentation, secret, whitespace, diff, and container-cleanup gates passed.
No production system was accessed. DB15 was not committed or pushed because
the execution package explicitly withheld those actions.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or production row data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match recorded authority.
