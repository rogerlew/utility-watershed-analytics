# DB04 — Legacy loader and observability guardrails

Status: `SCAFFOLDED`

Date: 2026-07-16

Roadmap item: `DB04`

Evidence mode: Mixed

Execution authorization: Not authorized. DB02 is not complete.

## Objective

Make destructive legacy watershed-loader flags fail closed in production and
eliminate unbounded Silk response capture before the runtime converges.

## Scope

Included:

- define explicit application environment detection;
- reject every production use of `load_watershed_data --force` before deletion;
- reject the globally destructive `--force --runids` combination in every
  environment while retaining safe non-production behavior;
- test all flag combinations, environment boundaries, and deletion ordering;
- disable Silk in production or implement and test accepted bounded retention;
- correct operator documentation and production Compose settings.

Excluded:

- implementing the release reconciler or emergency recovery loader;
- running the loader against production;
- deleting current Silk rows without separate production mutation authority;
- deploying before DB03 runtime convergence.

## Authority and inputs

- Dependency: DB02 `EXECUTED-COMPLETE`; production deployment follows DB03.
- Governing files: `docs/ROADMAP.md`, architecture Phase 0, current Django
  settings/URLs, loader command, Compose files, and deployment guide.
- Starting revision: freeze after DB02 completion.

## Assumptions and decisions

- Production detection must be explicit and fail closed; token presence,
  hostname, and `DEBUG` alone are insufficient authority signals.
- `--force --runids` is intrinsically unsafe because current code deletes all
  watersheds before loading a subset.
- Default target is to disable Silk middleware, URLs, and response capture in
  production unless an owner accepts a tested retention requirement.

## Plan

1. Freeze flag matrix and production environment contract.
2. Implement pre-delete guards and production Silk behavior.
3. Add exhaustive tests and production-configured container proof.
4. Reconcile operator documentation and deployment sequencing.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit: freeze after DB02 completion
- Working branch: assign at authorization review
- Push target: do not push unless separately authorized
- Pull-request target: do not open a PR unless separately authorized
- Authorized systems: repository/tests only when dependency is complete;
  production remains separately authorized
- Mutation boundary: loader/settings/URLs/Compose/tests/docs; no production data
- Executor and review assignments: assign implementer and independent destructive
  path reviewer before execution

## Gates

- Full backend Ruff and Django tests.
- Matrix for `--force`, `--runids`, `--all`, `--dry-run`, and combinations in
  development, test, and production settings.
- Proof production rejects before delete query/transaction begins.
- Production Silk middleware/URL/capture or retention behavior tests.
- Production image build and command execution against an isolated database.
- `git diff --check`, docs, and Compose render.

Skipped gate and reason:

- Execution: DB02 is incomplete and no package execution authority is recorded.
- Production deployment: requires DB03 and separate mutation authority.

## Exit criteria

`EXECUTED-COMPLETE` requires exhaustive automated guard and observability tests,
production-image proof, corrected docs, and dependency reconciliation.

Legitimate holds:

- `EXECUTED-HOLD-DEPENDENCY`: DB02 incomplete. First action: close DB02.
- `EXECUTED-HOLD-UNSAFE-FLAG`: any combination can delete before rejection.
  First action: preserve the failing test and move the guard earlier.

## Risks and recovery

- Risk: guard still allows partial destructive production load.
  - Prevention: reject before count/delete and test deletion mocks/queries.
  - Recovery or rollback: do not deploy; DB01 restore is not a substitute for a
    correct guard.
- Risk: disabling Silk removes needed diagnostics.
  - Prevention: owner review and ordinary structured logs/metrics.
  - Recovery or rollback: re-enable only through bounded tested configuration.

## Artifacts

- `artifacts/` — flag matrix, query/deletion proof, Silk behavior, container
  commands, and reviews.

## Execution record

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Scaffold review | repository only | Static | Blocked on DB02 completion. |

### Findings and deviations

- None; execution has not started.

### Terminal disposition

- Final status: pending dependency and authorization
- Exit criteria disposition: not executed
- Blocker, if held: DB02 incomplete
- First follow-on action, if held: complete DB02 production identity and proof
- Successor package, if any: production deploy after DB03; DB05 depends on DB04

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [ ] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
