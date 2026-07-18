# DB19A — Materialized capability runtime integration

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB19A`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic fixtures, isolated
server/client tests and builds, and disposable forest1 database acceptance. It
does not cover `wepp3`, real release/artifact access, production schema or
application mutation, real activation/adoption, commit, push, or a pull request.

## Objective

Make materialized active capability state the only authority for RHESSys and
release-declared SBS features after adoption, while preserving one exact,
observable `EMPTY` compatibility boundary until DB30A atomically activates a
release.

## Scope

Included:

- one central active-state/capability resolver for RHESSys and SBS;
- a strict public runtime-configuration contract with enabled/access policy,
  immutable index coordinates, geometry revision, scenarios, variables,
  spatial inputs, GeoTIFFs, Parquets, geometry, and artifact references;
- SBS as an explicit precomputed `RunCapability` type;
- exact `EMPTY` RHESSys allowlist and existing-watershed SBS fallback with
  structured logs;
- fail-closed `ACTIVE` absence, disablement, access, index/hash/base URI,
  geometry, scenario, variable, and artifact mismatch behavior;
- catalog, tile, geometry, dynamic Parquet query, SBS tile/download, and client
  eligibility/controls resolved from server capability metadata;
- positive/transition/mutation tests, isolated acceptance, CI, contracts,
  roadmap, catalog, and sanitized evidence.

Excluded:

- changing real capability rows, active pointer, production schema, release,
  artifact namespace, or upstream sources;
- real RHESSys/SBS discovery, durable copy, inventory assignment, or declaring
  any capability activation-ready;
- materialization/adoption/planning owned by DB20, DB30A, and DB31; and
- commit, push, pull request, or workflow dispatch.

## Authority and inputs

- DB15 ledger/capability contract: `docs/database-release-ledger-contract.md`.
- DB19 index/tooling contract:
  `docs/database-rhessys-artifact-tooling-contract.md`.
- Roadmap DB19A dual-compatible and proof requirements: `docs/ROADMAP.md`.
- Starting revision: `3d82885a2546ed689af78a85ac49a8d597be2d26`.

## Decisions

- State is checked before capability lookup. `ACTIVE` never falls back, even
  when a row is absent, disabled, malformed, or temporarily unhealthy.
- Legacy compatibility is intentionally hard-coded only on the `EMPTY` side.
  RHESSys uses the inventory-reviewed run/mode allowlist; SBS requires an
  existing serving watershed. Every use emits a sanitized structured log.
- Runtime configuration is public metadata only and is validated against the
  immutable `RunCapability` row. It may contain no credentials or derived
  WEPPcloud path convention.
- Materialized queries read the declared checksum-pinned Parquet artifact;
  client requests contain semantic dimensions, never dataset paths or SQL.
- Existing presentation registries may support `EMPTY` labels/rendering only;
  they do not grant eligibility or define `ACTIVE` assets.
- The accepted runtime behavior is frozen in
  `docs/database-capability-runtime-contract.md`.

## Plan

1. Freeze resolver and configuration shape.
2. Add SBS capability type migration.
3. Route every server data path.
4. Replace client-owned capability constants.
5. Prove EMPTY-to-ACTIVE transition.
6. Reconcile contracts and evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting/working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository, isolated Docker on `forest1`, and disposable
  test databases/containers
- Mutation boundary: DB19A code, migration, tests, docs, CI, fixtures, and
  disposable isolated test state
- Production server, database, artifact namespace, and active release: not
  authorized

## Gates

- `EMPTY` allowlisted behavior works and logs; non-allowlisted RHESSys does not
  probe. Switching to `ACTIVE` disables every fallback atomically.
- Active public/enabled rows expose exact metadata and declared assets; absent,
  disabled, private, malformed, mismatched, or wrong-release rows expose none.
- Catalog, tile, geometry, query, SBS tile/download, and client controls use
  capability metadata rather than run-derived paths or client lists.
- Durable materialized responses do not call legacy discovery/configuration;
  simulated upstream unavailability does not affect them.
- Migration, focused/full server, client lint/type/test/build, workflow, docs,
  secret, whitespace, and diff gates pass.

Skipped:

- production-shaped adoption transition: DB30A requires real reviewed release
  coordinates and separate production authority;
- real artifact query/render: DB30 locks real artifacts and DB21 provides full
  domain validation.

## Exit criteria

`EXECUTED-COMPLETE` requires resolver, all server/client integrations, exact
transition and negative proof, isolated acceptance, authoritative contracts,
catalog/roadmap reconciliation, and sanitized evidence.

## Artifacts

- `artifacts/db19a-validation-evidence.md`
- `docs/database-capability-runtime-contract.md`

## Execution record

- Added migration `watershed.0011_capability_runtime_types`, extending exact
  capability typing to release-declared precomputed SBS rows.
- Added one state-first resolver with strict public RHESSys/SBS configuration,
  exact observable `EMPTY` compatibility, and fail-closed `ACTIVE` behavior.
- Routed RHESSys catalog, spatial tiles, output tiles, geometry, semantic
  Parquet query, SBS tiles/downloads, and a public capability summary through
  that resolver.
- Removed client RHESSys run/scenario/variable/Parquet/geometry authority and
  run-derived SBS/RHESSys URLs; controls now consume API metadata.
- Passed 13 focused runtime tests, the full 173-test server suite, Ruff,
  migration drift, 587 client tests, ESLint, TypeScript, and production build.
- Used synthetic fixtures and disposable test databases only. No `wepp3`, real
  upstream artifact, production schema, active release, or `/wc1` production
  namespace was accessed or changed.
- Did not commit or push DB19A, matching the recorded execution boundary.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Evidence contains no credentials, real artifact coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match recorded authority.
