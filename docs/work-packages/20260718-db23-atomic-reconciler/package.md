# DB23 — Atomic desired-state reconciler

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB23`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic release/domain
fixtures, complete DB20 staging, disposable PostGIS, and concurrency proof on
forest1. It excludes `wepp3`, real releases/artifacts/plans, activation outside
disposable databases, commit, push, PR, and workflow dispatch.

## Objective

Apply one exact DB22 forward plan from a populated reviewed base to complete
validated DB20 staging in one short database transaction while preserving
stable public identities and unrelated application state.

## Decisions

- Regenerate and exactly compare the reviewed DB22 plan after acquiring the
  transaction advisory lock and active-pointer row lock.
- Extend DB20's canonical staged-row conversion and validation helpers; do not
  create another parser or serving-row writer.
- Reconcile retained children by stable business key and update their existing
  rows in place. A run replacement changes the physical run ID while retaining
  the logical identity, historical aliases, and matching child row IDs.
- Rebuild simplified geometry from canonical geometry only when geometry
  changes, except exact DB21A replay geometry already carried by staging.
- Install target-release capability rows from complete staging before the
  active pointer makes them visible; retain prior-release ledger rows.
- Retire only exact plan removals and leave persistent identities/aliases for
  compatibility and history.

## Gates

- `git diff --check`, Ruff, migration drift, focused DB23 tests, and complete
  server suite in the final production image.
- DB08/DB09 contracts and DB20/DB21/DB22 regression.
- Metadata, geometry, children, capability, add, remove, run replacement, and
  exact no-unrelated-mutation fixtures.
- Stable retained watershed/logical and child public identities.
- Wrong plan/base/staging and injected pre-commit failure roll back fully.
- Concurrent reader observes the committed old or new release, never partial
  serving state.
- Documentation, scope, secrets, links, and disposable cleanup.

## Execution record

- Extended DB20's serving mutation helpers so EMPTY build and populated
  reconciliation share canonical staged watershed, child, and capability row
  conversion and validation.
- Added exact populated-base activation under a transaction advisory lock and
  active-pointer row lock, complete DB22-plan regeneration/equality, base
  fingerprint/count reassertion, keyed in-place updates, exact removals,
  target capability installation, pointer advance, and final target
  fingerprint/count validation.
- Preserved matching child database IDs across metadata/geometry/child changes
  and run replacement, retained historical aliases, regenerated simplified
  geometry, and retired only the reviewed removal identity.
- Proved rollback after wrong plan, wrong active base, non-READY staging, and
  an injected failure after domain mutation but before capability/pointer
  advance. A paused two-connection PostGIS test observed the old committed
  release during mutation and the complete target after commit.
- Passed 19 combined DB20–DB23 tests and all 197 server tests in the final
  production image, plus DB08/DB09 validators and tests.
- Used synthetic rows and disposable PostGIS only. No `wepp3`, real release,
  production plan, production activation, commit, push, PR, or workflow
  dispatch occurred.

### Commands and evidence

| Gate | Result |
| --- | --- |
| Final production image build | Passed; `sha256:bcb69f9...` |
| Ruff and migration drift | Passed; no changes detected |
| Focused DB23 transaction proof | 3 passed in 6.136 seconds |
| Combined DB20–DB23 regression | 19 passed in 23.346 seconds |
| Final-image server regression | 197 passed in 73.955 seconds; one DB09 repository-schema integration skipped because schemas are outside the server image |
| DB08 schema contract | Validator plus 7 tests passed |
| DB09 fingerprint/plan contract | Validator plus 12 tests passed |

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met
- Blocker: none
- First follow-on action: scaffold DB24 reconciler resilience
- Successor package: DB24, not yet scaffolded

## Artifacts

- `artifacts/db23-validation-evidence.md`
- `docs/database-atomic-reconciler-contract.md`

## Closeout checklist

- [x] Package status/evidence mode are accurate.
- [x] Gates and skipped reasons are recorded.
- [x] Evidence contains no credentials, real coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match authority.
