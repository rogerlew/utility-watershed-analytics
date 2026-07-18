# DB21 — Validation, fingerprint, and clean-build CI

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB21`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic locked artifacts,
isolated server/release-contract tests, CI authoring, and disposable forest1
PostGIS acceptance. It does not cover `wepp3`, real release/artifact access,
production schema or application mutation, real activation/adoption, commit,
push, pull request, or workflow dispatch.

## Objective

Make a clean DB20 build independently checkable before acceptance and prove
that the same locked release produces identical serving-domain and capability
fingerprints in two fresh databases.

## Scope

Included:

- one shared DB09 canonical byte implementation for scripts and server code;
- locked artifact checks for safe URI, exact bytes/checksum/media, parseability,
  and rejection of saved HTML error bodies;
- staged run/release checks for exact membership/counts, geometry validity,
  world/release bounds, reasonable area coverage, and complete Parquet joins;
- active database checks and bounded serving-domain/capability fingerprints;
- application checks for list, stable detail, child GeoJSON, capability,
  removed-run, and representative materialized RHESSys query behavior;
- sanitized version-1 validation reports;
- two independent empty-build CI executions and exact fingerprint comparison;
- negative synthetic releases, contract tests, docs, and evidence.

Excluded:

- real release creation, identity assignment, artifact publication/download,
  production validation, adoption, non-empty planning/reconciliation, rollback,
  or deployment orchestration;
- changing DB09 fingerprint version or DB22 plan semantics;
- treating illustrative fixtures as production membership; and
- commit, push, pull request, or workflow dispatch.

## Authority and inputs

- Roadmap/architecture: `docs/ROADMAP.md` and
  `docs/database-deployment-architecture.md`.
- Fingerprint contract: `docs/database-fingerprint-plan-contract.md`.
- DB20 materializer: `docs/database-empty-materializer-contract.md`.
- Schemas: `data-releases/schema/v1/`.
- Starting revision: `8eb707e` (`Complete DB20 strict empty materializer`).

## Decisions

- DB09 canonical bytes remain version 1 and move to an importable pure module;
  the existing CLI/script remains a compatibility wrapper and golden parity is
  mandatory.
- DB21 serving fingerprints contain stable logical keys, canonical serving
  fields, normalized geometry bytes, child-set digests, and strict capability
  configuration. Database IDs, attempt/report timestamps, and audit rows are
  excluded.
- Artifact and staged validation runs before DB20 apply/activation. Database
  and application validation runs only against the complete disposable active
  build; later orchestration owns post-activation recovery policy.
- Geometry acceptance requires valid EPSG:4326 data inside world/reviewed
  bounds, children covered by the watershed, and a documented bounded
  subcatchment-to-watershed area ratio.
- CI uses two separate Django-created databases in independent container runs
  over the same synthetic locked fixture, then compares the complete sanitized
  fingerprint result bytes.

## Plan

1. Freeze validator and fingerprint subjects.
2. Share DB09 canonical byte code.
3. Add artifact and staging validators.
4. Add database and API validators.
5. Add double clean-build CI proof.
6. Run gates and reconcile docs.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit: `8eb707e`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository, isolated Docker on forest1, disposable test
  databases, and generated temporary artifact directories
- Mutation boundary: DB21 code, tests, workflow, docs, synthetic temporary
  files, and disposable database/container state
- Executor/reviewer: repository agent with operator review at handoff

## Gates

- `git diff --check`
- DB08/DB09 schema and fingerprint contract suites.
- Final production server image build, Ruff, and migration drift.
- Focused DB20/DB21 tests and full Django suite.
- Two independent exact-image empty builds produce byte-identical fingerprint
  results.
- Negative HTML, credential URI, geometry, count/join, API, removed-run, and
  RHESSys cases fail before being reported passed.
- Documentation links, workflow syntax/paths, secrets, and scope reviewed.

Skipped:

- production or real artifact validation: not authorized and belongs to later
  reviewed release packages;
- non-empty idempotency/rollback: DB22–DB24 own those mechanics;
- workflow dispatch: authoring/testing the workflow is authorized, dispatch is
  not.

## Exit criteria

`EXECUTED-COMPLETE` requires all five validator layers, canonical bounded
fingerprints, sanitized reports, two independent equal clean builds, required
negative and API/RHESSys proof, passing server/data-contract gates, and
reconciled authoritative docs/catalog/roadmap.

Legitimate hold outcome:

- `EXECUTED-HOLD-VALIDATION`: a required contract, focused/full server,
  exact-image, double-build, or workflow gate fails; record the exact blocker
  and first repair action.

## Risks and recovery

- Risk: a validator reimplements materializer semantics differently.
  - Prevention: validate DB20 locked inputs/staged rows and use the same
    canonical serving field maps.
  - Recovery: fail the attempt before apply and retain DB16 diagnostic staging.
- Risk: fingerprints vary with database IDs or unordered queries.
  - Prevention: stable logical keys, explicit ordering, versioned canonical
    bytes, and independent-process equality.
- Risk: smoke tests pass without reading declared RHESSys data.
  - Prevention: execute one semantic query through the public API against
    checksum-verified materialized Parquet.

## Artifacts

- `artifacts/db21-validation-evidence.md`
- `docs/database-clean-build-validation-contract.md`

## Execution record

- Extracted DB09 canonicalization into one pure importable module while
  retaining the original script/CLI API and golden compatibility suite.
- Added fatal artifact, staged run/release, active database, public
  application, and report validators around the existing DB20 writer.
- Added bounded serving-domain and capability fingerprints that exclude
  database IDs and audit/timing state while including logical identities,
  canonical geometry/serving fields, and strict runtime configuration.
- Composed DB20 apply, DB15 activation, database validation, and application
  validation in one outer transaction. Unsafe artifacts fail before staging;
  invalid staged geometry or a later check cannot accept partial serving state.
- Added CI that runs the same locked release through two independent
  container/test-database lifecycles and requires byte-identical fingerprint
  results.
- Passed final-image Ruff, migration drift, 10 focused tests, all 183 server
  tests, DB08/DB09 suites, workflow YAML parsing, and exact double-build proof
  against disposable PostGIS on forest1.
- Used synthetic artifacts only. No `wepp3`, real artifact namespace,
  production database, commit, push, PR, or workflow dispatch occurred.

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| `docker build -f server/Dockerfile --target production -t uwa-server:db21 server` | forest1 Docker | Ran | Passed; local image `sha256:411101f...` |
| Ruff, migration drift, and focused DB20/DB21 tests | final image plus disposable PostGIS | Ran | 10 tests passed in 10.156 seconds |
| Ruff, migration drift, and full Django suite | final image plus disposable PostGIS | Ran | 183 tests passed in 57.803 seconds |
| Two independent exact-image clean builds plus `cmp` | separate test-database lifecycles | Ran | Both passed; canonical output SHA-256 `4d1ed140...` |
| DB08 schema and DB09 fingerprint/plan suites | final image | Ran | 7 schema tests and 12 fingerprint tests passed |
| Workflow YAML, scope, secrets, docs, and diff review | repository | Mixed | Passed; see validation artifact |

### Findings and deviations

- Full validation remains in the server image because it depends on Django,
  DB15 ledger state, DB16 staging, DB20 mutations, and public API routes. The
  database-free preparation image keeps its simple structural `validate` and
  unavailable `build` commands instead of adding a second temporary interface.
- DB21 validates a complete empty build only. DB21A must first export and prove
  the unmanaged populated legacy base before adoption, and DB22–DB24 own
  reviewed non-empty planning, reconciliation, and recovery.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met
- Blocker: none
- First follow-on action: scaffold DB21A legacy-base export/adoption tooling
- Successor package: DB21A, not yet scaffolded

## Closeout checklist

- [x] Package status/evidence mode are accurate.
- [x] Gates and skipped reasons are recorded.
- [x] Evidence contains no credentials, real artifact coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match authority.
