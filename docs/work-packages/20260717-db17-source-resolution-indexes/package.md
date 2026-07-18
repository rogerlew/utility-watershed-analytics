# DB17 — Strict source resolution and exact member indexes

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB17`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-17. Authority covers repository changes, isolated tests and image
builds on `forest1`, and temporary acceptance data under the existing artifact
test namespace. It does not cover `wepp3`, production data, the production
artifact namespace, commit, push, or a pull request.

## Objective

Implement the smallest strict preparation path that resolves standalone and
batch sources exactly once, binds every discovered member to a reviewed stable
identity, publishes verified immutable bytes through DB12, and emits a
deterministic DB08 exact-member index that can be reproduced without mutable
upstream access.

## Scope

Included:

- one versioned preparation descriptor for either a standalone run or batch;
- explicit source URLs, custom batch master filenames, reviewed member/run/key
  bindings, source revision, fixed output timestamp, and optional secret
  reference resolved only from the environment;
- strict streamed fetch with status and declared-length checks;
- GeoJSON feature-collection, identity, count, finite-coordinate, and bounds
  validation plus Parquet envelope validation;
- exact batch membership comparison with empty, missing, extra, and duplicate
  member rejection;
- deterministic per-member metadata and boundary artifacts;
- immutable publication and re-fetch verification through DB12's local
  content-addressed artifact client;
- deterministic DB08 batch-member index and source receipt publication;
- receipt replay using only cached immutable inputs, with no upstream calls;
- DB11 `prepare` command wiring, stable structured failures, status reporting,
  tests, image proof, CI, documentation, roadmap, catalog, and evidence; and
- isolated synthetic acceptance under the forest1 test namespace.

Excluded:

- real release membership, production source resolution, production artifact
  publication, `wepp3`, credentials, or production data;
- NASA enrichment, RHESSys discovery, database staging/reconciliation,
  deployment plans, activation, rollback, or removal authority;
- changes to legacy runtime loader discovery; and
- commit, push, pull request, or workflow dispatch.

## Authority and inputs

- DB08 schema contract: `docs/database-release-schema-contract.md`.
- DB11 CLI contract: `docs/database-release-tool-contract.md`.
- DB12 artifact client: `docs/database-artifact-client-contract.md`.
- Stable identity authority: `docs/database-identity-metadata-contract.md`.
- Starting revision: `319bf717d570cb42356ef5e4b88f90e60c612ba2`.

## Decisions

- Preparation never guesses a stable key. The descriptor's reviewed member map
  must equal batch discovery exactly; missing or extra upstream members fail.
- The descriptor supplies the master URL directly, so a custom master filename
  is ordinary data rather than a derived naming convention.
- Mutable inputs are streamed into private temporary files. They are published
  only after complete transport and format validation.
- Version 1 validates the Parquet file envelope and footer boundary without
  adding a Parquet dependency to the code-only release-tool image. DB21 owns
  dataset-specific schemas and semantic validation.
- Every artifact reference uses the caller-supplied credential-free public
  HTTPS base URI while DB12 stores the authoritative bytes on forest1.
- A source receipt contains URLs, roles, byte counts, and hashes but no header
  or secret value. Replay requires exact descriptor/receipt coordinates and
  fetches every input by digest from DB12.
- Fixed descriptor time plus canonical JSON makes repeat preparation from the
  same immutable inputs byte-identical.
- `prepare` becomes available; the remaining DB11 successor commands remain
  explicitly unavailable.

## Plan

1. Add descriptor and strict transport models.
2. Implement batch and standalone preparation.
3. Publish and replay immutable inputs.
4. Wire CLI and structured failures.
5. Prove negative cases and reproducibility.
6. Reconcile docs, CI, and evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch: `agent/database-backup-deployment-spec`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository, isolated Docker on forest1, and a temporary
  subtree below `/wc1/utility-watershed-analytics-artifacts/v1/test`
- Mutation boundary: DB17 code, tests, docs, CI, disposable fixtures, caches,
  image builds, and temporary test-namespace objects
- Production server and production namespace: not authorized

## Gates

- Standalone and batch happy paths emit structurally valid exact member indexes
  and verified immutable artifacts.
- Empty upstream results, missing/extra members, duplicate run IDs, custom
  master filename, partial download, malformed GeoJSON, malformed Parquet, and
  missing required source all fail before an index is published.
- Repeat preparation from a receipt performs zero upstream reads and produces
  the exact same index bytes, digest, membership, and artifact references.
- Secret values never enter indexes, receipts, logs, errors, or image layers.
- Artifact publication is confined to a temporary forest1 test subtree and
  leaves that subtree absent after acceptance.
- Release-tool unit tests, acceptance wrapper, reproducible image build/audit,
  Python compilation, Ruff, workflow, documentation, secret, whitespace, and
  `git diff --check` gates pass.

Skipped:

- real WEPPcloud preparation: no reviewed real DB17 descriptor/member mapping
  or real release output was authorized;
- database/server/client tests: DB17 changes only the code-only release tool;
- production and deployment gates: successor packages own them.

## Exit criteria

`EXECUTED-COMPLETE` requires both adapters, exact membership, fatal required
source behavior, immutable publication/replay, all named negative fixtures,
reproducible image proof, authoritative documentation, catalog, roadmap, and
sanitized evidence.

Legitimate hold outcomes:

- `EXECUTED-HOLD-IDENTITY`: a discovered source member cannot be bound without
  guessing a stable reviewed identity;
- `EXECUTED-HOLD-FORMAT`: required source bytes cannot be validated without
  expanding the accepted toolchain; or
- `EXECUTED-HOLD-REPLAY`: repeat preparation requires mutable upstream access.

## Artifacts

- `artifacts/db17-validation-evidence.md`

## Execution record

- Added one standard-library preparation module with closed version-1
  descriptors, strict HTTPS transport, exact identity/membership comparison,
  GeoJSON and Parquet-envelope validation, and deterministic serialization.
- Published every required input, generated metadata/boundary artifact, final
  DB08 index, and source receipt through DB12 with digest re-fetch verification.
- Activated the DB11 `prepare` command while preserving all other unavailable
  successor commands and the structured event/exit-code contract.
- Passed 40 release-tool tests, six source-acceptance/image-verifier tests, the
  existing artifact acceptance wrapper, and actual DB08 schema/semantic checks
  for generated standalone and batch indexes.
- Passed real forest1 acceptance under the test namespace with six batch and
  six standalone inputs, nine immutable objects, byte-identical receipt replay,
  and complete temporary-subtree removal.
- Reproducibly built and audited image
  `sha256:8332c517002e819ead3dbaf2480fe479209175d0365ad5e92010f854c08e89ce`.
- Did not access a real upstream, credential, real membership, `wepp3`, or the
  production artifact namespace.
- Did not commit, push, open a pull request, or dispatch a workflow for DB17,
  matching recorded authority.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets, real membership, or source data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match recorded authority.
