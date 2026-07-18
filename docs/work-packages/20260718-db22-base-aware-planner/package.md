# DB22 — Base-aware planner and exact inverse

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB22`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic ledger/domain
fixtures, plan generation, schema validation, and disposable PostGIS on
forest1. It excludes `wepp3`, real releases/artifacts, production plans,
activation, commit, push, PR, and workflow dispatch.

Subsequent publication authorization: after DB22 reached
`EXECUTED-COMPLETE`, the operator separately authorized committing and pushing
the completed package to the current branch. PR creation and workflow dispatch
remain outside scope.

## Objective

Generate deterministic reviewed-base forward, exact-inverse, and independently
derived EMPTY-build plans from immutable DB15/DB21 state without mutating it.

## Decisions

- Stable watershed key is the action identity; run replacement is a change,
  not an unrelated remove/add.
- Compatibility and observed active fingerprints are fatal preconditions.
- Change channels derive only from immutable run-state fingerprints/counts.
- Large removals require one explicit reviewed override; thresholds are fixed
  and never warnings.
- Exact inverse is a mechanical mirror bound to the canonical forward-plan
  digest. Empty-build planning is independently derived from the target.

## Gates

- Ruff, migration drift, focused planner tests, and complete server suite.
- DB08/DB09 schema/fingerprint contract suites.
- Deterministic repeated-process bytes for all three plan kinds.
- Metadata, geometry, replacement, collection expansion/shrink, capability,
  compatibility, unknown/drifted base, and removal-threshold fixtures.
- Documentation, links, secrets, scope, and disposable cleanup.

## Execution record

- Added a read-only planner that locks and exactly checks the active reviewed
  base, recomputes its serving fingerprint, rejects incompatible release,
  schema, materializer, contract, or validation coordinates, and compares
  stable watershed membership.
- Added exact deterministic add/change/remove/retain classification, canonical
  change-channel ordering and row deltas, fixed removal refusal, mechanical
  forward-bound inverse generation, and independently derived EMPTY-build
  generation.
- Added `generate_release_plans`, which emits the complete DB09 plan bundle and
  refuses to overwrite an existing output.
- Passed six synthetic DB22 tests including native DB09 plan schemas and
  semantics, all 194 server tests, and the complete DB08/DB09 contract suites
  using the final production image and disposable PostGIS on forest1.
- Used synthetic release/domain state only. During governed execution, no
  `wepp3`, real release, production plan, activation, commit, push, PR, or
  workflow dispatch occurred; repository publication was separately authorized
  after completion.

### Commands and evidence

| Gate | Result |
| --- | --- |
| Final production image build | Passed; `sha256:53d95a8...` |
| Ruff and migration drift | Passed; no changes detected |
| Focused mounted DB22 proof | 6 passed in 1.821 seconds |
| Final-image server regression | 194 passed in 65.759 seconds; one repository-schema test skipped because schemas are intentionally outside the server image |
| DB08 schema contract | Validator plus 7 tests passed |
| DB09 fingerprint/plan contract | Validator plus 12 tests passed |

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met
- Blocker: none
- First follow-on action: scaffold DB23 atomic desired-state reconciler
- Successor package: DB23, not yet scaffolded

## Artifacts

- `artifacts/db22-validation-evidence.md`
- `docs/database-base-aware-planner-contract.md`

## Closeout checklist

- [x] Package status/evidence mode are accurate.
- [x] Gates and skipped reasons are recorded.
- [x] Evidence contains no credentials, real coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match authority.
