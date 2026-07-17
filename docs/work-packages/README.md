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
| [20260716-db01-backup-restore-baseline](20260716-db01-backup-restore-baseline/package.md) | DB01 | `EXECUTED-HOLD-PRODUCTION-DRILL` | `forest1:/wc1/utility-watershed-analytics-db-backups`, single-operator ownership, 24-hour RPO/RTO, local alerts, encryption, timers, retention, and isolated restore are accepted and exercised; representative `wepp3` transport/restore and reboot evidence remain required. |
| [20260716-db02-production-runtime-bundle](20260716-db02-production-runtime-bundle/package.md) | DB02 | `EXECUTED-HOLD-PRODUCTION-IDENTITY` | Target runtime, lock, identity, socket, workflow, unit, and isolated gates passed; authorized production identity/reachability freeze and runtime proof remain required. |
| [20260716-db03-production-runtime-convergence](20260716-db03-production-runtime-convergence/package.md) | DB03 | `SCAFFOLDED` | Not authorized; blocked on DB01/DB02 completion and separate production read/mutation authority. |
| [20260716-db04-legacy-loader-guardrails](20260716-db04-legacy-loader-guardrails/package.md) | DB04 | `SCAFFOLDED` | Not authorized; blocked on DB02 completion, with production deployment following DB03. |
| [20260716-db05-named-postgres-volume-cutover](20260716-db05-named-postgres-volume-cutover/package.md) | DB05 | `SCAFFOLDED` | Not authorized; blocked on DB01/DB03/DB04, rehearsal, accepted RTO, and production cutover authority. |
| [20260716-db06-domain-identity-audit](20260716-db06-domain-identity-audit/package.md) | DB06 | `EXECUTED-HOLD-PRODUCTION-EVIDENCE` | Ownership/identity audit, deterministic read-only command, production-image build, and 110 tests passed; the empty development database cannot prove production counts, uniqueness, or dirty-data absence. |
