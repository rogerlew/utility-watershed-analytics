# DB19 — RHESSys vendor, index, and validation tooling

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB19`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic fixtures, isolated
tests and image builds on `forest1`, and temporary acceptance data below the
artifact test namespace. It does not cover real RHESSys sources or inventory
descriptors, `wepp3`, production data/namespaces, runtime activation, commit,
push, or a pull request.

## Objective

Prepare reviewed dynamic and precomputed RHESSys assets into the operator-owned
local artifact store, fail closed on structural or compatibility drift, and
emit deterministic immutable capability indexes and replay receipts.

## Scope

Included:

- one closed `rhessys-capability` descriptor routed through `prepare`;
- dynamic, precomputed, and combined modes with exact scenario/variable
  coverage and activation requirements;
- checksum, size, geometry revision, Parquet physical schema, spatial ID,
  variables/units/year range, and GeoTIFF CRS/bounds/dimensions/bands/nodata;
- bounded real Parquet footer inspection and classic GeoTIFF metadata/sample
  reads without adding GDAL, Arrow, a provider SDK, or paid infrastructure;
- DB12 content-addressed local publication, re-fetch verification, DB08 index,
  receipt-only replay, and explicit removed-key calculation;
- DB08 scenario/physical-column schema completion and DB09 fingerprint updates;
- named negative fixtures, forest1 `/wc1` test acceptance, reproducible image,
  CI, authoritative contracts, roadmap, catalog, and sanitized evidence.

Excluded:

- real WEPPcloud discovery, source inspection, inventory membership, durable
  production publication, or declaring any current run activation-ready;
- Parquet row/value/join/year statistics, BigTIFF, indirect CRS keys, or
  transform-only GeoTIFF georeferencing;
- database materialization, runtime capability integration, current discovery
  changes, client changes, activation, adoption, or production planning; and
- `wepp3`, commit, push, pull request, or workflow dispatch.

## Authority and inputs

- Deployment architecture: `docs/database-deployment-architecture.md`, section
  8.6.
- Inventory: `docs/database-inventory.md`, RHESSys inventory.
- DB08 schemas: `docs/database-release-schema-contract.md`.
- DB12 local artifact client: `docs/database-artifact-client-contract.md`.
- DB17 source preparation: `docs/database-source-preparation-contract.md`.
- Binding storage decision: `forest1:/wc1`; no provider may be selected.
- Starting revision: `0b75d58c3796495fe03334765b418b625705b6e6`.

## Decisions

- The descriptor is exact and closed rather than a discovery engine. It cannot
  infer scenarios, variables, paths, stable identities, or geometry revisions.
- The immutable index now carries required scenarios and flat Parquet physical
  columns because the architecture requires them and runtime must not depend on
  the unpublished descriptor.
- The code-only image reads bounded Parquet footer metadata and classic GeoTIFF
  tags directly. Unsupported variants fail closed; DB21 owns domain row reads.
- Precomputed modes require exact declared scenario/variable coverage. Missing,
  partial, duplicate, or extra pairs fail before publication.
- Capability removal is the sorted exact difference between reviewed previous
  and successor key sets. DB19 does not mutate serving rows.
- The index's HTTPS base URI is a serving coordinate, not a storage-provider
  decision. DB12 writes the actual bytes to the supplied local `/wc1` namespace.

## Plan

1. Freeze descriptor and index fields.
2. Implement bounded format inspection.
3. Publish immutable assets and receipt.
4. Add mutation and removal fixtures.
5. Rehearse local replay on forest1.
6. Reconcile schema, docs, and evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting/working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository, isolated Docker on `forest1`, and one
  disposable subtree below
  `/wc1/utility-watershed-analytics-artifacts/v1/test`
- Mutation boundary: DB19 code, schemas, tests, docs, CI, disposable fixtures,
  caches, image builds, and temporary test-namespace objects
- Production server and namespace: not authorized

## Gates

- Dynamic, precomputed, and combined descriptor rules fail closed.
- Missing/partial scenarios, renamed variables, physical schema drift, corrupt
  GeoTIFF, CRS mismatch, geometry mismatch, interrupted publication, and
  capability removal have focused proof.
- Generated indexes pass actual DB08 structural/semantic validation and DB09
  fingerprints remain deterministic and order-insensitive.
- Receipt replay makes no upstream reads and reproduces exact bytes/hashes.
- Forest1 acceptance uses and completely removes only its `/wc1/v1/test`
  temporary subtree.
- Release-tool, acceptance, schema, fingerprint, image, Python, workflow,
  documentation, secret, whitespace, and diff gates pass.

Skipped:

- real RHESSys input/durable copy: DB30 owns reviewed real descriptors/assets;
- runtime integration: DB19A owns materialized capability resolution;
- row/domain validation and database staging: DB20–DB21 own these boundaries;
- production adoption/planning: DB30A/DB31 own later authorized operations.

## Exit criteria

`EXECUTED-COMPLETE` requires code, every named mutation proof, DB08/DB09
reconciliation, local `/wc1` acceptance cleanup, reproducible image proof,
contracts, catalog, roadmap, and sanitized evidence without real or production
access.

## Artifacts

- `artifacts/db19-validation-evidence.md`

## Execution record

- Added one closed RHESSys preparer routed through the existing `prepare`
  command, with separate dynamic, precomputed, and combined mode rules.
- Added bounded Compact Protocol Parquet footer/schema inspection and classic
  GeoTIFF CRS, bounds, dimensions, bands, nodata, and strip/tile sample reads.
- Published checksum/size-pinned inputs, exact DB08 index, and replay receipt
  through DB12 with re-fetch verification and zero-upstream exact replay.
- Completed DB08 scenarios and Parquet physical columns, then reconciled DB09
  normalization, order-insensitivity proof, linked fixtures, and golden hashes.
- Passed 58 release-tool tests and 11 acceptance/image wrapper tests, including
  every named DB19 positive, mutation, interruption, and removal case.
- Passed actual DB08 schema/semantic validation for the generated index and all
  seven schemas/nine negative fixtures; DB09's five subjects/four schemas/three
  plans/twelve tests also passed.
- Passed real isolated forest1 acceptance below `/wc1/.../v1/test` with four
  sources, two scenarios, content-addressed re-fetches, exact replay, explicit
  one-key removal, and exact pre/post namespace equality.
- Reproducibly built and audited code-only image
  `sha256:14fd35b2cbfeac308cd796e466af1acf59c29f5e70ddea72cfa950a057217b42`.
- Did not inspect real RHESSys inputs, access `wepp3`, touch the production
  artifact namespace, choose a provider, publish a real release, or change
  runtime/serving state.
- Did not commit, push, open a pull request, or dispatch a workflow for DB19,
  matching recorded authority.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no real RHESSys coordinates, assets, credentials, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match recorded authority.
