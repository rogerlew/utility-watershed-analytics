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
