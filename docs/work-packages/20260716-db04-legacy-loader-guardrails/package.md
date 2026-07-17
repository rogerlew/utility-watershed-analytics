# DB04 — Legacy loader and observability guardrails

Status: `EXECUTED-COMPLETE`

Date: 2026-07-16

Roadmap item: `DB04`

Evidence mode: Mixed

Execution authorization: The user's 2026-07-17 request to “scaffold and execute
DB04” authorizes the bounded repository implementation, isolated development
tests, commit, and push. Production access and deployment remain excluded.

## Objective

Make destructive legacy watershed-loader flags fail closed in production and
eliminate unbounded Silk response capture before the next application deploy.

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
- deploying this repository change to production.

## Authority and inputs

- Dependencies: DB02 and DB03/DB03A `EXECUTED-COMPLETE` for this repository
  work. Any production deployment requires separate authority.
- Governing files: `docs/ROADMAP.md`, architecture Phase 0, current Django
  settings/URLs, loader command, Compose files, and deployment guide.
- Starting revision: `1a1e5e867595d90f447b0e2e812a284755f92025`.

## Assumptions and decisions

- Production detection must be explicit and fail closed; token presence,
  hostname, and `DEBUG` alone are insufficient authority signals.
- `--force --runids` is intrinsically unsafe because current code deletes all
  watersheds before loading a subset. Bare `--force` has the same defect because
  it defaults to the development subset, so safe non-production force requires
  `--all`.
- Default target is to disable Silk middleware, URLs, and response capture in
  production unless an owner accepts a tested retention requirement.

## Plan

1. Freeze flag matrix and production environment contract.
2. Implement pre-delete guards and production Silk behavior.
3. Add exhaustive tests and production-configured container proof.
4. Reconcile operator documentation and deployment sequencing.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit:
  `1a1e5e867595d90f447b0e2e812a284755f92025`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: current branch and fast-forward-only fork `main`
- Pull-request target: do not open a PR unless separately authorized
- Authorized systems: repository/tests only when dependency is complete;
  production remains separately authorized
- Mutation boundary: loader/settings/URLs/Compose/tests/docs; no production data
- Executor/reviewer: Codex implements and reviews the bounded patch; the
  exhaustive automated flag matrix independently enforces destructive-path
  ordering for this single-operator repository.

## Gates

- Full backend Ruff and Django tests.
- Matrix for `--force`, `--runids`, `--all`, `--dry-run`, and combinations in
  development, test, and production settings.
- Proof production rejects before delete query/transaction begins.
- Production Silk middleware/URL/capture or retention behavior tests.
- Production image build and command execution against an isolated database.
- `git diff --check`, docs, and Compose render.

Skipped gate and reason:

- Production deployment: separately authorized production mutation is not part
  of DB04 repository execution.

## Exit criteria

`EXECUTED-COMPLETE` requires exhaustive automated guard and observability tests,
production-image proof, corrected docs, and dependency reconciliation.

Legitimate holds:

- `EXECUTED-HOLD-DEPENDENCY`: a future prerequisite regresses or becomes
  invalid. First action: restore the exact prerequisite without weakening the
  guardrails.
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
| Authority and dependency reconciliation | repository / DB01–DB03A evidence | Static | DB02 and DB03/DB03A complete; user authorized bounded DB04 repository execution, tests, commit, and push. Production remained excluded. |
| Environment and loader implementation | repository | Static / Ran tests | Explicit three-value `APP_ENVIRONMENT` contract added. Production force, partial force, ambiguous selection, and unknown environment reject before the first database query. |
| Silk production disablement | repository / isolated settings process | Ran | Production excludes the Silk app, middleware, and URL; development/test retain it. No existing Silk row was touched. |
| Focused flag and ordering suite | development container | Ran | Five DB04 tests passed, including all 48 environment/flag combinations, pre-query rejection sentinels, and safe non-production delete/load ordering. |
| Full backend gates | development container | Ran | Ruff passed and all 115 Django tests passed against the isolated Django test database. |
| Production-image proof | `forest1` containers | Ran | Image `sha256:3c58c34...` built; Ruff and all 115 tests passed. Production force and partial force commands rejected without DB connectivity; production Silk assertions and Compose render passed. |
| Documentation and package reconciliation | repository | Static / Ran | README/deployment guidance, roadmap, catalog, DB05 dependency, evidence, links, and diff checks reconciled. |

### Findings and deviations

- Bare `--force` was as unsafe as explicit `--force --runids` because it selected
  `DEV_RUNIDS` after deleting all rows. DB04 therefore requires `--all` for any
  non-production force rather than guarding only the explicit subset flag.
- The first production-image test launch lacked the local ignored environment
  in its calling shell and stopped before test creation. It was rerun through a
  non-logging local environment load and passed.
- An inline production Silk URL assertion initially had invalid shell newline
  escaping. The corrected equivalent assertion passed; no behavioral change
  was needed.
- Production deployment was not authorized or performed. The guards are
  repository-complete but are not claimed active on `wepp3`.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: environment, flag-matrix, pre-query rejection,
  safe ordering, Silk, Ruff, full-test, production-image, Compose, and docs gates
  passed
- Blocker, if held: none
- First follow-on action, if held: not applicable
- Successor package, if any: DB05 remains separately authorized production work

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
