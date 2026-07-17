# DB02 — Canonical production runtime bundle

Status: `EXECUTED-HOLD-PRODUCTION-IDENTITY`

Date: 2026-07-16

Roadmap item: `DB02`

Evidence mode: Mixed

Execution authorization: User-authorized Wave 0 orchestration on 2026-07-16,
limited to repository mutation and isolated non-production execution on
`forest1`. Production inspection and mutation are not authorized.

## Objective

Create a fail-closed repository-owned production runtime contract: canonical
Compose identity, exact PostGIS pin input, internal-only service sockets,
mode-`0600` minimized runtime environment, safe systemd behavior, explicit
migrations, no-recreate identity checks, and one composable cross-principal
host operations lock.

## Scope

Included:

- define the canonical checkout, Compose file, target project name, and unit;
- require an exact existing-production PostGIS image reference without choosing
  or upgrading it from development evidence;
- remove direct server and database host publication from target production
  Compose while preserving public Caddy ports;
- define mode-`0600` minimized runtime environment handling and cleanup;
- replace ordinary `down` behavior with application-only stop semantics;
- implement the absolute host-wide operations lock, inherited nested lock
  contract, boot-time ownership, and contention/cancellation tests;
- serialize application deployment, run migrations explicitly, and verify the
  database container/image/volume identity before and after proposed actions;
- render and exercise the contract only in isolated `forest1` fixtures.

Excluded:

- inspecting the currently running `wepp3` image, project, container, volume,
  systemd unit, principals, listeners, firewall, or Compose labels;
- installing or activating the target unit or Compose file on `wepp3`;
- changing production services, sockets, environment modes, or lock ownership;
- neutralizing the loaded legacy production unit or adopting the target
  contract, which belongs to DB03;
- adding the named PostgreSQL volume or moving data, which belongs to DB05.

## Authority and inputs

- Governing roadmap: `docs/ROADMAP.md`, Wave 0, DB02.
- Governing specification: `docs/database-deployment-architecture.md`, sections
  14.1, 19.1, 20, and Phase 0.
- Review closure: `docs/database-deployment-roadmap-review.md`, findings O3,
  O4, O11, and O14.
- Starting revision:
  `30a9077d432a5c8582759b614e0ea7224713b685` plus preserved local Wave 0 and DB01
  authoring changes.
- Observed development state: `docs/wave-0-readiness.md`.
- Production observed state: unavailable under this package's authority. Any
  earlier inventory prose is not a substitute for a fresh identity freeze.

## Assumptions and decisions

- Canonical checkout target: `/workdir/utility-watershed-analytics`.
- Canonical Compose file: `compose.prod.yml`.
- Canonical final project target: `utility-watershed-analytics`. DB03 must
  reconcile this with the observed running project without database recreate.
- Exact PostGIS image: supplied through required `POSTGIS_IMAGE` only after an
  authorized read records the running repository digest and version. No
  fallback tag is allowed in production Compose.
- Canonical lock: `/run/lock/utility-watershed-analytics/operations.lock`,
  owned by `root:uwa-operators`, mode `0660`, with parent mode `0770`.
- Application deploy, migration, data activation, scheduled/on-demand backup,
  restore, volume work, recovery, and legacy mutation participate in the same
  lock. Read-only backup may use shared mode; mutation uses exclusive mode.
- Nested orchestration inherits a verified open lock descriptor and mode;
  shared holders cannot request an exclusive nested operation.
- The target systemd stop action stops only application-facing services. It
  never invokes `docker compose down` and never stops or removes the database.

## Plan

1. Implement lock, identity preflight, and isolated contention fixtures.
2. Harden Compose, systemd, runtime environment, and deployment workflow.
3. Render and exercise no-recreate, socket, unit, cancellation, and reboot-static gates.
4. Record unresolved production identities and terminalize honestly.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit: `agent/database-backup-deployment-spec` at
  `30a9077d432a5c8582759b614e0ea7224713b685`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository working tree and disposable non-production
  processes, files, networks, and containers on `forest1`
- Mutation boundary: repository files and disposable DB02 fixtures; running
  development database/API services and unrelated shared workloads must not be
  stopped or reconfigured
- Executor and review assignments: Codex authors and validates; operator owns
  production identity freeze, principal mapping, firewall review, and DB03
  authorization

## Gates

Always:

- `git diff --check`
- Package diff reviewed against included and excluded scope.

Applicable checks:

- ShellCheck, syntax, safe lock fixtures, nested invocation, contention,
  cancellation, and stale descriptor rejection;
- Compose production render with an explicit non-production image digest;
- static socket inventory proving only Caddy publishes production host ports;
- no-recreate identity preflight against an isolated labeled fixture;
- `systemd-analyze verify`, start/stop/reload fixture behavior, and explicit
  proof no command contains `down` or database stop/remove;
- workflow/YAML and minimized environment handling review;
- host lock boot recreation through tmpfiles static verification.

Skipped gate and reason:

- actual production image/project/container/volume/listener/firewall identity:
  production read-only access is not authorized;
- actual operator/systemd/CI runner group contention: production identities are
  not observed or provisioned on `forest1`;
- production unit activation, reboot, socket reachability, and rollback:
  production mutation is not authorized and belongs to DB03.

## Exit criteria

`EXECUTED-COMPLETE` requires:

- current production PostGIS image is frozen exactly without upgrade;
- canonical/interim/final identities and no-recreate adoption are proven;
- every internal published socket is removed or loopback-bound and reachability
  is tested from Compose, localhost, Tailscale, and public interfaces;
- the shared/exclusive/inherited lock passes actual cross-principal, nested,
  cancellation, reboot, and contention tests;
- unit start/stop/reload and rollback preserve the exact database container,
  image, and source volume;
- runtime environment mode/content and cleanup pass;
- authoritative docs, roadmap, and catalog are reconciled.

Legitimate hold outcomes:

- `EXECUTED-HOLD-PRODUCTION-IDENTITY`: repository and isolated gates pass, but
  exact production image/project/container/volume/unit/principals/listeners or
  firewall behavior remain unauthorized or unknown. First follow-on: authorize
  a read-only identity freeze and reconcile the adoption plan before DB03.
- `EXECUTED-HOLD-RECREATE-RISK`: proposed adoption would recreate or detach the
  database. First follow-on: preserve identities and revise the interim plan;
  never apply the proposal.

## Risks and recovery

- Risk: target project or Compose changes recreate the anonymous-volume
  database.
  - Prevention: exact identity freeze, config-hash/action inspection,
    `--no-deps` application changes, and before/after assertions.
  - Recovery or rollback: do not apply; retain the running project and source
    volume, then revise the interim contract.
- Risk: an inherited lock token bypasses serialization or deadlocks a nested
  backup.
  - Prevention: canonical descriptor/path/mode validation, shared/exclusive
    rules, bounded waits, and nested/contention/cancellation fixtures.
  - Recovery or rollback: cancel the outer orchestrator, verify the descriptor
    closed, inspect protected state, and rerun only after base identity checks.
- Risk: hardening disconnects required operator access.
  - Prevention: Compose-peer access plus explicit localhost/Tailscale/public
    reachability matrix and firewall assumptions before production apply.
  - Recovery or rollback: application-only rollback under the lock; never
    invoke `down` or replace the database.

## Artifacts

- `artifacts/` — sanitized renders, identity fixture, lock and unit results,
  socket matrix, environment checks, and review notes.

## Execution record

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| DB02 scope and production boundary review | `forest1`, 2026-07-16 | Mixed | Repository and isolated execution authorized; production identity and mutation excluded. |
| `scripts/tests/test_operation_lock.sh` | disposable `forest1` processes/file | Ran | Nested shared/exclusive, shared contention, concurrent readers, cancellation 143, reacquisition, and stale-descriptor boundaries passed. |
| Runtime environment fixtures | `forest1` temporary files | Ran | Minimized mode-`0600` digest-pinned fixture passed; mode `0644`, extra superuser key, and unpinned image failed closed. |
| Production Compose render and app-only dry-run | `forest1`, explicit development fixture digest | Ran | Only Caddy publishes 80/443; server/db are internal; app-only plan proposed no database action. |
| Database identity capture/assert and tamper fixture | running development database, read-only | Ran | Unchanged identity passed and altered expected ID failed. No production inference. |
| ShellCheck, Actionlint, systemd verify, Ruff, Django tests, production image build | `forest1` and pinned tool containers | Ran | Passed; 106 Django tests and production image build passed. See `artifacts/forest1-runtime-evidence.md`. |
| Production identity, principal, reachability, unit, reboot, and rollback gates | `wepp3` | Static | Not run; production read and mutation were not authorized. |

### Findings and deviations

- Exact production runtime identities remain intentionally unknown and must not
  be inferred from the development image or old prose.
- `systemd-analyze verify` rejected the initially proposed
  `ConditionPathIsRegular`. It was replaced with a valid `ConditionPathExists`
  plus an executable owner/mode/symlink/key/digest runtime check.
- A tmpfiles create rehearsal could not apply root/group ownership as the
  development user and was retained as Static syntax/contract evidence only.

### Terminal disposition

- Final status: `EXECUTED-HOLD-PRODUCTION-IDENTITY`
- Exit criteria disposition: repository target, lock, environment, Compose,
  systemd, workflow, identity guard, socket render, app-only dry-run, backend,
  and image-build gates passed; all actual production identities and runtime
  behavior remain unmet.
- Blocker, if held: production read-only identity freeze is unauthorized, DB01
  remains on external decisions, and production mutation is unauthorized.
- First follow-on action, if held: authorize a read-only `wepp3` identity and
  reachability freeze, then reconcile the exact interim no-recreate actions and
  cross-principal lock ownership before considering DB03.
- Successor package, if any: DB03 only after DB01 and DB02 complete plus
  explicit production mutation authority; DB04 remains dependency-blocked.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
