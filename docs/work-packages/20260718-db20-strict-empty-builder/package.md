# DB20 — Strict empty-database materializer

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB20`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic fixtures, isolated
server tests, and a disposable forest1 database acceptance. It does not cover
`wepp3`, real release or artifact access, production schema or application
mutation, real activation or adoption, commit, push, or a pull request.

## Objective

Replace permissive serving-table loader writes with a strict bounded-memory
materializer that verifies locked artifacts, produces canonical attempt-scoped
rows, and atomically builds an exact release into an empty serving base through
reusable mutation primitives.

## Scope

Included:

- locked local artifact size, checksum, role, and media-type verification;
- bounded GeoJSON and Parquet ingestion into DB16 staging tables;
- exact watershed, child, metadata, attribute, and declared capability rows;
- strict per-run counts, joins, geometry, and deterministic ordering;
- reusable EMPTY-base mutation primitives and whole-attempt failure behavior;
- synthetic multi-run/mixed-source tests and disposable PostGIS acceptance;
- authoritative contract, evidence, roadmap, and catalog reconciliation.

Excluded:

- release planning, ledger or identity creation, artifact downloading, and
  source resolution, which remain DB09, DB12, DB15, and DB17 inputs;
- fingerprints, independent clean-build CI, full application validation, and
  reports owned by DB21;
- non-empty apply, legacy adoption, production activation, or rollback owned
  by later roadmap packages; and
- `wepp3`, real release data, commit, push, pull request, or workflow dispatch.

## Authority and inputs

- Roadmap and architecture: `docs/ROADMAP.md` and
  `docs/database-deployment-architecture.md`.
- Staging and ledger contracts: `docs/database-staging-recovery-contract.md`
  and `docs/database-release-ledger-contract.md`.
- Locked source and capability contracts: DB17, DB19, and DB19A artifacts and
  schemas under `data-releases/schema/v1/`.
- Starting repository revision: `d778ec3a4fe95aba91fcef3946e4374f70f907a0`.

## Decisions

- DB20 accepts existing validated release/run/identity ledger rows. It does not
  infer reviewed identities, plans, or fingerprints from filenames.
- Every input is an ordinary local file with an exact expected byte size,
  SHA-256 digest, role, and media type. Symlinks and changed artifacts fail.
- GeoJSON features and Parquet batches are consumed incrementally. Canonical
  keys must be strictly ordered, which provides duplicate and ordering proof
  without retaining an unbounded key set.
- Staging may retain diagnostic residue, but serving rows and the active
  singleton remain unchanged unless every required member validates.
- EMPTY-base application is one transaction and uses only validated staged
  rows. The primitive deliberately does not activate the release; later
  orchestration retains the reviewed-plan and activation gates.

## Plan

1. Freeze locked-input and canonical-row contract.
2. Add bounded staging writer primitives.
3. Implement strict artifact materializer.
4. Add atomic EMPTY-base mutations.
5. Run focused and isolated acceptance.
6. Reconcile contract and evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit: `d778ec3a4fe95aba91fcef3946e4374f70f907a0`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository, isolated Docker on `forest1`, and disposable
  test databases/containers
- Mutation boundary: DB20 code, tests, docs, synthetic fixtures, and disposable
  isolated database state
- Executor and reviewer: repository agent, with operator review at handoff

## Gates

- `git diff --check`
- Production server image build and Ruff.
- Focused DB20 tests and full Django suite in the production image.
- Disposable PostGIS acceptance using only generated synthetic artifacts.
- Multi-run exact counts/relationships and deterministic staged snapshots.
- Bad required input leaves no serving-domain or active-pointer mutation.
- Observed GeoJSON/Parquet batch size never exceeds the configured bound.
- Documentation paths, commands, and authority boundaries reviewed.

Skipped:

- production execution: not authorized and not needed for DB20 proof;
- real release/artifact acceptance: DB21 and later packages own reviewed data;
- real release activation: not authorized; synthetic disposable activation
  through the existing DB15 helper is part of the atomicity proof.

## Exit criteria

`EXECUTED-COMPLETE` requires strict locked-artifact ingestion, deterministic
canonical staging, reusable atomic EMPTY-base application, exact multi-run and
failure proof, bounded geometry/Parquet evidence, passing server gates, and
reconciled authoritative documentation.

Legitimate hold outcome:

- `EXECUTED-HOLD-VALIDATION`: a required focused, full-suite, image, or
  disposable PostGIS gate fails; record the failure and first repair action.

## Risks and recovery

- Risk: a malformed or changed required artifact partially stages a release.
  - Prevention: verify every locked file first and accept only a READY attempt.
  - Recovery: retain bounded diagnostic staging and fail the attempt; serving
    rows remain untouched.
- Risk: a failed apply leaves a partially populated empty base.
  - Prevention: lock/assert EMPTY and apply every serving mutation in one
    transaction.
  - Recovery: transaction rollback restores the unchanged empty base.
- Risk: large artifacts cause unbounded memory use.
  - Prevention: GDAL feature iteration, PyArrow record batches, database
    iterators, and configured bulk-operation bounds.

## Artifacts

- `artifacts/db20-validation-evidence.md`
- `docs/database-empty-materializer-contract.md`

## Execution record

- Added strict local-file verification against immutable DB15 lineage, exact
  metadata/member coordinates, incremental GDAL geometry reads, and PyArrow
  record-batch Topaz joins.
- Extended DB16 with bounded per-model loads and an explicit READY finalizer
  while retaining the original compatibility wrapper and recovery semantics.
- Added reusable EMPTY-base assertions and serving mutations for canonical
  watershed, child, and strict capability rows.
- Composed apply and DB15 activation in one outer transaction; both a bad
  required Parquet and a late strict capability failure preserved `EMPTY` with
  zero accepted partial serving rows.
- Passed the final production-image build, 14 focused DB20/DB16 tests, Ruff,
  migration drift, and the complete 177-test server suite against disposable
  PostGIS on forest1.
- Used synthetic artifacts only. No `wepp3`, real artifact namespace,
  production database, commit, push, PR, or workflow action occurred.

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| `docker build -f server/Dockerfile --target production -t uwa-server:db20 server` | forest1 Docker | Ran | Passed; local image `sha256:3141d3d...` |
| Ruff, migration drift, and focused materializer/staging tests in final image | final `uwa-server:db20` plus disposable PostGIS | Ran | 14 tests passed in 15.753 seconds |
| Ruff, migration drift, and full Django suite | final `uwa-server:db20` plus disposable PostGIS | Ran | 177 tests passed in 48.363 seconds |
| Locked input, canonical rows, EMPTY apply, and successor boundary review | repository | Static | Accepted in `docs/database-empty-materializer-contract.md` |
| Scope, secret, documentation, and diff review | repository | Mixed | Passed; see validation artifact |

### Findings and deviations

- The database-free preparation image cannot safely implement its reserved
  `build` command before DB21 validators and DB22 reviewed plan inputs exist.
  DB20 therefore exposes the executable server-image materializer and preserves
  the fail-closed command rather than inventing a temporary second input/writer.
- Diagnostic staging chunks intentionally survive pre-READY failure under the
  DB16 recovery contract; they never become serving state.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met
- Blocker: none
- First follow-on action: scaffold DB21 clean-build validation/fingerprinting
- Successor package: DB21, not yet scaffolded

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Evidence contains no credentials, real artifact coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match recorded authority.
