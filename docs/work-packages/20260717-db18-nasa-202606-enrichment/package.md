# DB18 — Deterministic NASA 202606 enrichment

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB18`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-17. Authority covers repository changes, synthetic fixtures, isolated
tests and image builds on `forest1`, and temporary acceptance data below the
artifact test namespace. It does not cover real target discovery, real release
publication, `wepp3`, production data or namespaces, commit, push, or a pull
request.

## Objective

Implement the inventory's one fixed NASA 202606 metadata enrichment: join a
checksum-pinned WWS source to the reviewed successor target by unique
`WWS_Code`, preserve exact target membership, run IDs, feature order, and
geometry, copy only the twelve approved fields, and publish deterministic
output, validation, provenance, and member-index artifacts.

## Scope

Included:

- one DB17 batch-descriptor extension for `nasa-202606-wws-code` enrichment;
- required source HTTPS URL, SHA-256, byte count, code commit, and validator
  image digest;
- fixed `WWS_Code` join and the twelve inventory-approved source properties;
- target-authoritative `runid`, geometry, feature count/order, and all
  non-enrichment properties;
- rejection of absent/null join keys, duplicate keys, conflicting preexisting
  target values, wrong target run prefix, source checksum/size mismatch, and
  any post-transform membership, run-ID, or geometry change;
- explicit matched, target-unmatched, source-unmatched, and duplicate counts;
- canonical enriched GeoJSON, DB08 validation report, transformation lineage,
  and exact member-index lineage references published through DB12;
- receipt-only deterministic replay with no upstream access;
- positive and mutation fixtures, forest1 test-namespace acceptance,
  reproducible image proof, CI, durable docs, roadmap, catalog, and evidence.

Excluded:

- fetching the real NASA target master, using the real WWS source, assigning
  real member identities, or publishing a real release;
- inventing sources for `OwnerType`, `PopGroup`, `TreatType`, `ConnGroup`, or
  `HUC10_*` utility aggregates absent from the approved WWS input;
- copying historical source `runid` or source geometry;
- database staging/materialization, current-loader changes, validation beyond
  the DB18 artifact boundary, activation, old-batch removal, or production
  snapshot updates; and
- commit, push, pull request, workflow dispatch, or production access.

## Authority and inputs

- Inventory enrichment contract: `docs/database-inventory.md`, NASA 202606
  resources enrichment section.
- DB07 authority matrix: `docs/database-identity-metadata-contract.md`.
- DB08 lineage/report schemas: `docs/database-release-schema-contract.md`.
- DB12 artifact client: `docs/database-artifact-client-contract.md`.
- DB17 source preparer: `docs/database-source-preparation-contract.md`.
- Starting revision: `bea4a99ca30938b145c6546fcf64ea362a9f59fb`.

## Decisions

- DB18 is not a generic join engine. Its transform name, join key, copied field
  set, target prefix, authority, and validation rules are constants in code.
- The descriptor must checksum-pin the enrichment source before parsing. The
  documented real source coordinates remain inventory facts, not execution
  authority for this package.
- Missing target/source `WWS_Code` and duplicates are fatal. Unmatched unique
  keys are allowed only when counted: unmatched target features retain their
  target `WWS_Code` and receive the other approved fields as explicit null;
  source-only keys are not added.
- A non-null target value for an approved field must equal the source value or
  the transform fails. Equal values pass; null or absent values take the source
  authority. No other target property changes.
- Historical source `runid` and source geometry are ignored. Output validation
  compares exact target run IDs, geometry JSON, feature count, and order.
- Successful lineage records unmatched target plus source counts in DB08's
  aggregate `unmatched` field and preserves both counts separately in the
  validation report.
- Fixed descriptor time and canonical JSON make output, report, lineage, index,
  and receipt byte-identical during immutable replay.

## Plan

1. Add fixed NASA enrichment transform.
2. Extend the strict preparation descriptor.
3. Publish report and lineage artifacts.
4. Add positive and mutation fixtures.
5. Rehearse immutable replay on forest1.
6. Reconcile docs, CI, and evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch: `agent/database-backup-deployment-spec`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository, isolated Docker on forest1, and one
  disposable subtree below
  `/wc1/utility-watershed-analytics-artifacts/v1/test`
- Mutation boundary: DB18 code, tests, docs, CI, disposable fixtures/caches,
  image builds, and temporary test-namespace objects
- Production server and production namespace: not authorized

## Gates

- Positive fixtures prove exact join, approved fields, unchanged run IDs,
  geometries, order, count, and non-enrichment properties.
- Missing/null and duplicate join keys, conflicting values, source size/hash
  mismatch, wrong target prefix, post-transform geometry/run-ID change, and
  member-count change fail closed.
- Unmatched target/source keys are counted without dropping or adding target
  features; target unmatched fields are explicit null.
- Historical source run IDs and differing source geometry never enter output.
- Generated exact member index, transformation lineage, and validation report
  pass the real DB08 schema and semantic validators.
- Receipt replay makes zero upstream reads and reproduces exact output, report,
  lineage, index, receipt, and hashes.
- The real forest1 acceptance subtree is removed completely.
- Release-tool tests, acceptance wrappers, reproducible image/audit, Python,
  Ruff, workflow, docs, secret, whitespace, and diff gates pass.

Skipped:

- real NASA source/target validation and production snapshot update: DB30 owns
  real locked inputs and DB30A/DB31 own production adoption/planning;
- isolated database staging build: DB20 materialization and DB21 validation are
  prerequisites not yet implemented;
- server/client suites: DB18 changes only the code-only release tool.

## Exit criteria

`EXECUTED-COMPLETE` requires the fixed transform, strict preparation
integration, every named positive/negative proof, DB08-valid provenance,
immutable replay, forest1 and image acceptance, authoritative docs, catalog,
roadmap, and sanitized evidence.

Legitimate hold outcomes:

- `EXECUTED-HOLD-AUTHORITY`: the inventory leaves field or precedence authority
  ambiguous;
- `EXECUTED-HOLD-INTEGRITY`: output can change target membership, run IDs, or
  geometry; or
- `EXECUTED-HOLD-LINEAGE`: successful bytes cannot be represented by the DB08
  lineage/report contracts.

## Artifacts

- `artifacts/db18-validation-evidence.md`

## Execution record

- Added one closed `nasa-202606-wws-code` transform with a fixed join, target
  prefix, twelve approved fields, precedence, unmatched semantics, preservation
  validator, and fourteen lineage decisions.
- Extended DB17 batch descriptors with checksum/size-pinned enrichment input,
  code revision, and validator image coordinates.
- Published canonical enriched GeoJSON, DB08 validation report and
  transformation lineage, per-member lineage references, exact member index,
  and source receipt through DB12 with re-fetch verification.
- Passed 47 release-tool tests and nine acceptance/image-verifier wrapper tests,
  including every named DB18 positive and mutation case.
- Passed actual DB08 schema and semantic validation for the generated member
  index, transformation lineage, and validation report.
- Passed real forest1 acceptance with two exact target members, one match, one
  target-only key, one source-only key, twelve required sources, fourteen field
  decisions, historical-authority comparison, byte-identical replay, and full
  temporary-subtree removal.
- Reproducibly built and audited image
  `sha256:cd7db4255485d6767ca6fd02fa52d35735afe564284a359de0dc9d9ef18ae355`.
- Did not fetch either real NASA input, assign real membership, access `wepp3`,
  publish a real release, or touch the production artifact namespace.
- Did not commit, push, open a pull request, or dispatch a workflow for DB18,
  matching recorded authority.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no real membership, source data, credentials, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match recorded authority.
