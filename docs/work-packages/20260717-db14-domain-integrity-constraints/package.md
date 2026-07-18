# DB14 — Watershed-domain integrity constraints

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB14`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-17. Authority covers repository changes and isolated forest1 PostGIS,
container, migration, lock-observation, failure-fixture, and rollback tests.

## Objective

Make the accepted watershed-domain identities enforceable without closing the
DB13 compatibility window: constrain legacy and logical child keys, stable key
formats and identity status, reject ambiguous analytical joins, and freeze the
exact rebuild/cascade boundary.

## Scope

Included:

- additive database/model constraints for collection and watershed stable-key
  formats and logical-identity status;
- unique legacy and logical business keys for subcatchments and channels, with
  logical constraints applying only to already-linked rows;
- explicit rejection of null or duplicate Topaz join identities in hillslope,
  soil, and land-use Parquet inputs;
- a pre-constraint migration audit that fails with aggregate-only findings;
- an executable ownership registry for the three reconciled serving tables,
  protected identity tables, delete order, and Django/database deletion rules;
- updated aggregate identity audit output for compatibility and logical keys;
- duplicate, orphan, invalid-key, invalid-status, join, cascade/protection, and
  non-domain preservation tests;
- a production-shaped isolated migration rehearsal with duration and observed
  PostgreSQL lock modes; and
- authoritative integrity/ownership documentation, roadmap, catalog, package,
  and sanitized evidence.

Excluded:

- production or `wepp3` access or mutation;
- making DB13 logical links or unreviewed watershed keys non-null;
- new normalized soil, land-use, hillslope, batch-revision, release-ledger, or
  staging tables;
- database triggers for cross-table logical-link agreement;
- reconciler implementation, data activation, production rollout, commit,
  push, or pull request.

## Authority and inputs

- DB06 evidence: `docs/database-domain-identity-audit.md`.
- DB07 identities: `docs/database-identity-metadata-contract.md` section 3.
- DB13 compatibility: `docs/database-watershed-identity-migration.md`.
- Architecture: `docs/database-deployment-architecture.md` sections 9.1–9.4.
- Starting revision: `907cd7e191da7a4501908653611caf273fb64527`.
- Accepted production aggregate: 126 watersheds, 195,457 subcatchments, 86,895
  channels, zero accepted-key duplicates, and zero child orphans.

## Assumptions and decisions

- Compatibility keys remain `(watershed_id, topazid)` and
  `(watershed_id, topazid, weppid, order)` while DB13's old foreign keys exist.
- Accepted logical keys are `(logical_watershed_id, topazid)` and
  `(logical_watershed_id, topazid, weppid, order)`. Their unique constraints are
  partial while the additive links remain nullable.
- One `Subcatchment` row owns its hillslope, soil, and land-use payloads. The
  child uniqueness constraint therefore enforces the database target identity;
  each incoming Parquet artifact separately rejects null or duplicate Topaz
  joins before mapping.
- `WatershedCollection` represents the stable batch/standalone grouping.
  Source batch revision and exact member uniqueness remain DB08 artifact-schema
  responsibilities until release-ledger models exist.
- Reconciliation may replace only `Watershed`, `Subcatchment`, and `Channel`
  serving rows. Stable identity/alias tables persist and may be deliberately
  updated but are never wholesale rebuild targets.
- Django deletes children before a watershed. PostgreSQL foreign keys reject a
  raw parent delete until children are removed. Identity and collection deletes
  are protected while any serving row, child, or alias references them.

## Plan

1. Add model and migration integrity constraints.
2. Reject ambiguous Parquet join identities.
3. Freeze ownership and deletion behavior in code/docs.
4. Add database, loader, audit, and migration tests.
5. Rehearse production shape and observe locks.
6. Reconcile roadmap, catalog, package, and evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch: `agent/database-backup-deployment-spec`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository and isolated Docker/PostGIS on forest1
- Mutation boundary: DB14 code, migrations, tests, documentation, and
  disposable test databases/containers
- Production server and production database: not authorized

## Gates

- Django migration graph and `makemigrations --check` pass.
- Focused constraints reject duplicate compatibility/logical child keys,
  invalid stable keys/status, and old/logical FK orphans.
- Hillslope, soil, and land-use loaders reject null and duplicate Topaz joins.
- Ownership tests prove only the three serving tables are rebuild-owned; ORM
  cascade order and database/identity protection match the contract.
- Auth users, sessions, admin/control tables, identity rows, and aliases survive
  a bounded serving-domain rebuild fixture.
- Production-shaped forward/rollback migration preserves counts and IDs,
  reports duration, and records observed relation lock modes.
- Production server image build, Ruff, focused/full Django tests, docs/secret/
  whitespace checks, and `git diff --check` pass.

Skipped:

- production migration timing: DB27A requires separate production schema and
  application mutation authority;
- non-null logical-link contraction: incompatible with the documented additive
  rollout point;
- client suite: no client behavior changes.

## Exit criteria

`EXECUTED-COMPLETE` requires enforceable accepted keys and joins, explicit
rebuild/cascade ownership, all negative fixtures, production-shaped migration
and lock evidence, full server gates, and reconciled durable documentation.

Legitimate hold outcomes:

- `EXECUTED-HOLD-DIRTY-DATA`: the accepted production-shaped input cannot
  satisfy a proposed constraint;
- `EXECUTED-HOLD-LOCKING`: isolated migration lock/duration exceeds the bounded
  rehearsal expectation or cannot be observed reliably.

## Risks and recovery

- Risk: a constraint closes old-code compatibility.
  - Prevention: retain legacy keys and make logical uniqueness partial while
    logical links remain nullable.
- Risk: duplicate analytical joins silently select one row.
  - Prevention: reject null or duplicate Topaz identities before `set_index`.
- Risk: rebuild scope deletes auth, session, observability, or identity history.
  - Prevention: executable three-table allowlist and preservation tests.
- Risk: unique-index creation blocks writers longer than expected.
  - Recovery: reverse the additive constraints before identity-aware successor
    work; production rollout later uses its own measured lock budget.

## Artifacts

- `artifacts/db14-validation-evidence.md` — sanitized constraints, ownership,
  migration duration/locks, image, and validation evidence.

## Execution record

Implemented migration `0008_domain_integrity_constraints`, the matching model
constraints, fail-closed Topaz join validation, aggregate audit contract v2,
and an executable three-table ownership registry. Added database, loader,
migration, cascade/protection, rebuild-boundary, and aggregate-audit tests.

The focused suite passed 15 tests. A synthetic production-shaped isolated
PostGIS rehearsal passed with 126 watersheds, 195,457 subcatchments, and 86,895
channels. Forward migration took 2.128 seconds, reverse took 0.213 seconds, and
669 lock samples observed the expected granted relation lock modes. Negative
duplicate, orphan, and invalid-key writes failed. Counts, sampled child IDs,
identity rows, aliases, one synthetic auth row, and one synthetic session were
preserved.

The final production image is
`sha256:dce9341b992435712845784d202332e99bd1c42aa07c94191d0da17118c00478`.
Ruff, migration drift checking, all 138 server tests, Python syntax,
documentation, secret, whitespace, diff, and container-cleanup gates passed.
No production system was accessed. DB14 was not committed or pushed because
the execution package explicitly withheld those actions.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or production row data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match recorded authority.
