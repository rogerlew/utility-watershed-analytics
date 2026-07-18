# Work Packages

Work packages are the repository's bounded execution records. The convention
is adapted from `cligen-rs` at commit `7adce50`: keep the process light, but do
not relax honest terminal states, evidence discipline, explicit dispatch, or
roadmap reconciliation.

The [roadmap](../ROADMAP.md) answers “what remains and in what order?” A work
package answers “what exactly was authorized, done, checked, and learned?” A
design specification remains authoritative for system behavior; a package is
the execution record for a bounded slice of that design.

## Layout

Use one directory per unit of work:

```text
docs/work-packages/
  YYYYMMDD-<short-slug>/
    package.md
    kickoff-prompt.md       # optional; recommended for delegated execution
    artifacts/              # evidence produced during execution
```

Start from [the package template](templates/package.md). When work will be
delegated or resumed in a separate session, also use the
[kickoff-prompt template](templates/kickoff-prompt.md).

Package names are immutable. If a hold, changed approach, or expanded scope
requires successor work, create a new directory and link the predecessor.

## Status and authorization

Allowed package states are:

- `SCAFFOLDED`: scoped for review but not necessarily authorized.
- `EXECUTED-COMPLETE`: all exit criteria and applicable gates passed.
- `EXECUTED-HOLD-<REASON>`: execution ended without satisfying the complete
  criteria; the exact blocker and first follow-on action are recorded.

Do not use optimistic states such as “mostly complete,” silently stop a
package, or mark a review finding resolved because prose was added. A hold is
an honest terminal record, not a failure to document the work.

Status is separate from authority. Every package records whether execution is
authorized, by whom or by what review, and the allowed mutation boundary.
Repository changes do not imply permission to access or mutate production.
Production read-only access, production mutation, remote pushes, and pull
request creation must each be explicit when applicable.

## Evidence discipline

Label material claims and the package as one of:

- **Ran**: observed by executing the recorded command in the named environment.
- **Static**: concluded from source, configuration, documentation, or review
  without executing the affected behavior.
- **Mixed**: combines both; identify which evidence supports each conclusion.

Record commands, environment or host, relevant versions or revisions, dates,
and output paths. Preserve compact durable evidence in `artifacts/`; do not
commit credentials, environment files, raw production dumps, or bulky
generated data. A passing command proves only the boundary it exercised.

Operational claims need operational evidence. For example, a shell syntax
check does not prove a restore, a dry run does not prove transaction rollback,
and a local build does not prove the production deployment path.

## Workflow

1. **Select:** choose an unblocked roadmap item and identify authoritative
   specifications, inventories, and observed-state evidence.
2. **Scaffold:** copy the templates into a new immutable package directory;
   make included and excluded scope, dependencies, risks, and exit criteria
   checkable.
3. **Review and authorize:** confirm the package's authority, mutation
   boundary, dispatch coordinates, gates, and hold outcomes before execution.
4. **Execute:** work within scope, record decisions and commands as they occur,
   and save reviewable artifacts. Amend the package when reality changes the
   plan.
5. **Gate and review:** run every applicable repository and package-specific
   check. Record skipped gates with a reason; do not represent Static review as
   Ran evidence.
6. **Close honestly:** set `EXECUTED-COMPLETE` only when every exit criterion is
   met. Otherwise terminalize with a specific hold, blocker, and first
   follow-on action.
7. **Reconcile:** update this catalog, remove completed work from the forward
   roadmap, add or refine remaining work, and update authoritative documents
   when the package established durable facts.

## Dispatch rules

Every handoff or kickoff prompt must state:

- repository path or URL;
- exact starting branch or commit;
- working branch;
- push remote and branch, or explicitly “do not push”;
- pull-request target, or explicitly “do not open a PR”;
- documents to read first;
- authorized systems and mutation boundary; and
- expected deliverables, gates, evidence, and terminal-state behavior.

An executor must preserve unrelated local changes and stop before any
unapproved external mutation. If execution occurs from an unstated base or is
pushed to an unstated target, record the divergence and reconcile it rather
than hiding it.

## Gate selection

Every package runs `git diff --check` and selects the relevant project gates.
Use the repository workflows as the source of truth for exact commands:

- backend changes: `.github/workflows/server-ci.yml`;
- frontend changes: `.github/workflows/client-ci.yml`;
- deployment integration: `.github/workflows/deploy.yml` plus package-specific
  non-production or explicitly authorized operational checks;
- shell changes: syntax checks and ShellCheck when available;
- documentation changes: links, paths, code fences, and commands checked
  against the repository state; and
- data releases: manifest/schema validation, exact membership and removal
  plans, checksums, clean-build fingerprints, application smoke tests, backup,
  and rollback evidence as required by the architecture.

A package may add stronger gates. It may skip an irrelevant gate only with a
recorded reason.

## Catalog

| Package | Roadmap item | Status | Disposition |
| --- | --- | --- | --- |
| [20260716-db01-backup-restore-baseline](20260716-db01-backup-restore-baseline/package.md) | DB01 | `EXECUTED-COMPLETE` | Permanent restricted transport, production scheduling, encrypted backup, success/failure/freshness, journal alerting, exact isolated restore, non-empty smoke, 376-second RTO, and post-reboot timer/snapshot persistence passed. The unsafe legacy runtime registration is disabled/not-found; its source and evidence are retained for DB02. |
| [20260716-db02-production-runtime-bundle](20260716-db02-production-runtime-bundle/package.md) | DB02 | `EXECUTED-COMPLETE` | Fail-closed target runtime, lock, identity, socket, workflow, unit, isolated gates, exact production identity freeze, current reachability, and DB03 adoption boundary passed without production mutation. |
| [20260716-db03-production-runtime-convergence](20260716-db03-production-runtime-convergence/package.md) | DB03 | `EXECUTED-HOLD-PUBLISH` | Historical host-convergence package: every production gate passed and its publication hold is resolved by completed successor DB03A. |
| [20260717-db03a-production-runner-ownership-closure](20260717-db03a-production-runner-ownership-closure/package.md) | DB03A | `EXECUTED-COMPLETE` | Safe fork `main`, protected secret delivery, checksum-pinned fork runner, online/idle service proof, old-runner disablement, unchanged runtime/database, and temporary-privilege removal passed without dispatching a job. |
| [20260716-db04-legacy-loader-guardrails](20260716-db04-legacy-loader-guardrails/package.md) | DB04 | `EXECUTED-COMPLETE` | Explicit environment contract, 48-case pre-query destructive-flag matrix, production Silk disablement, full 115-test suites, production-image negative commands, Compose render, and operator docs passed without production access. |
| [20260716-db05-named-postgres-volume-cutover](20260716-db05-named-postgres-volume-cutover/package.md) | DB05 | `EXECUTED-COMPLETE` | Rehearsal and production named-volume cutover, rollback/reapply, persistence/reboot, encrypted pre/post backup, exact fingerprints, isolated restore, fork `main` publication, and clean production checkout convergence passed with the anonymous source retained for DB05A. |
| [20260716-db06-domain-identity-audit](20260716-db06-domain-identity-audit/package.md) | DB06 | `EXECUTED-COMPLETE` | Ownership/identity mapping, deterministic read-only tooling, production-image build, 110 tests, and a separately authorized aggregate production audit passed with 126 watersheds, 195,457 subcatchments, 86,895 channels, zero duplicate groups, zero child orphans, and no production mutation. |
| [20260717-db07-identity-metadata-contract](20260717-db07-identity-metadata-contract/package.md) | DB07 | `EXECUTED-COMPLETE` | Version-1 collection/watershed keys, replaceable source aliases, child identities, lineage, route compatibility, field authority/null/conflict rules, nine accepted lifecycle fixtures, three rejected conflicts, and seven validator/model-coverage tests passed without application or production changes. |
| [20260717-db08-release-index-schemas](20260717-db08-release-index-schemas/package.md) | DB08 | `EXECUTED-COMPLETE` | Seven Draft 2020-12 schemas, complete positive coverage, nine focused rejection cases, bounded semantic and credential checks, cross-file membership proof, and reusable CI wiring passed on `forest1` without production access. |
| [20260717-db09-fingerprint-plan-contract](20260717-db09-fingerprint-plan-contract/package.md) | DB09 | `EXECUTED-COMPLETE` | Version-1 canonical bytes and golden SHA-256 values for five semantic subjects, four plan schemas, exact forward/inverse and empty-build proof, twelve mutation tests, and wrong-base replay rejection passed without production access. |
| [20260717-db10-artifact-store-contract](20260717-db10-artifact-store-contract/package.md) | DB10 | `EXECUTED-COMPLETE` | Amended to the operator-authorized `forest1:/wc1` filesystem contract with one owner, private paths, content-addressed copies, active-plus-two retention, six artifact classes, seven failure cases, and ten fail-closed tests. No provider was provisioned. |
| [20260717-db10a-artifact-store-infrastructure](20260717-db10a-artifact-store-infrastructure/package.md) | DB10A | `EXECUTED-COMPLETE` | Real forest1 test/production paths, private modes, three-release fixture backup, collision/corruption/missing/partial/unavailable-path rejection, idempotent rerun, capacity check, and exact clean restore passed. |
| [20260717-db11-release-tool-foundation](20260717-db11-release-tool-foundation/package.md) | DB11 | `EXECUTED-COMPLETE` | Eight stable commands, JSON events, named exit codes, verified read-only input, fatal future-command boundaries, 16 unit tests, reproducible double-build image ID, content audit, and immutable-ID runtime proof passed without real release data or production access. |
| [20260717-db12-artifact-client-cache](20260717-db12-artifact-client-cache/package.md) | DB12 | `EXECUTED-COMPLETE` | Streaming immutable publish/fetch, checksum and cache recovery, interruption and concurrency proof, typed failures, private environment-isolated paths, bounded retained/leased cache cleanup, real forest1 temporary acceptance, and reproducible audited image passed. |
| [20260717-db13-watershed-identity-migration](20260717-db13-watershed-identity-migration/package.md) | DB13 | `EXECUTED-COMPLETE` | Additive UUID-backed logical identities, exact accepted stable-key assignments, permanent current/historical run aliases, dual child links, stable-key API routes and feature IDs, canonical browser redirects, aggregate validation, old-code compatibility, replacement preservation, and production-shaped forward/rollback proof passed without production access. |
| [20260717-db14-domain-integrity-constraints](20260717-db14-domain-integrity-constraints/package.md) | DB14 | `EXECUTED-COMPLETE` | Seven database constraints, fail-closed Topaz joins, exact three-table rebuild ownership and delete order, identity/auth/session preservation, 15 focused tests, and synthetic production-shaped migration, rollback, and lock evidence passed without production access. |
| [20260717-db15-release-ledger-capabilities](20260717-db15-release-ledger-capabilities/package.md) | DB15 | `EXECUTED-COMPLETE` | Version-1 release/run/artifact history, bootstrapped singleton, operator/workflow attempts, one bounded lease, sanitized failures, helper-gated lifecycle, rollback reactivation, and active-only RHESSys capability visibility passed focused and production-shaped isolated PostGIS proof. |
| [20260717-db16-staging-recovery-schema](20260717-db16-staging-recovery-schema/package.md) | DB16 | `EXECUTED-COMPLETE` | Five logged attempt-scoped tables, exact artifact/staging/index/backup/WAL/margin preflight, bounded chunk loading, heartbeat, crash residue, every non-terminal expiry, retention, cleanup failure/retry, and active-state preservation passed isolated PostGIS proof. |
| [20260717-db17-source-resolution-indexes](20260717-db17-source-resolution-indexes/package.md) | DB17 | `EXECUTED-COMPLETE` | Strict standalone/batch preparation, exact reviewed membership, fatal transport/format failures, immutable local publication, DB08 indexes, and receipt-only replay passed isolated forest1 proof. |
| [20260717-db18-nasa-202606-enrichment](20260717-db18-nasa-202606-enrichment/package.md) | DB18 | `EXECUTED-COMPLETE` | Fixed checksum-pinned `WWS_Code` enrichment, target-authoritative membership/run IDs/geometry, exact approved fields, conflicts, DB08 provenance, and immutable replay passed synthetic forest1 proof. |
| [20260718-db19-rhessys-artifact-tooling](20260718-db19-rhessys-artifact-tooling/package.md) | DB19 | `EXECUTED-COMPLETE` | Closed dynamic/precomputed preparation, exact scenario/variable and Parquet schema metadata, bounded TIFF/Parquet reads, geometry compatibility, immutable `/wc1` test publication, explicit removal difference, and replay passed synthetic forest1 proof. |
| [20260718-db19a-capability-runtime-integration](20260718-db19a-capability-runtime-integration/package.md) | DB19A | `EXECUTED-COMPLETE` | State-first RHESSys/SBS resolution, exact observable `EMPTY` compatibility, fail-closed `ACTIVE` behavior, declared durable server reads, semantic Parquet queries, and API-owned client controls passed synthetic server/client proof. |
| [20260718-db20-strict-empty-builder](20260718-db20-strict-empty-builder/package.md) | DB20 | `EXECUTED-COMPLETE` | Checksum-locked metadata/GeoJSON/Parquet, bounded canonical staging, exact EMPTY-base watershed/child/capability mutation, deterministic replay, and whole-attempt rollback passed final-image and full-suite disposable PostGIS proof. |
| [20260718-db21-clean-build-reproducibility](20260718-db21-clean-build-reproducibility/package.md) | DB21 | `EXECUTED-COMPLETE` | Fatal five-layer clean-build validation, bounded logical serving/capability fingerprints, sanitized write-once reports, negative artifact/geometry proof, public API/RHESSys reads, and two byte-identical independent disposable builds passed without production access. |
