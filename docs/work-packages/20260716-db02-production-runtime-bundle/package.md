# DB02 — Canonical production runtime bundle

Status: `EXECUTED-COMPLETE`

Date: 2026-07-16

Roadmap item: `DB02`

Evidence mode: Mixed

Execution authorization: User-authorized Wave 0 orchestration on 2026-07-16,
initially limited to repository mutation and isolated non-production execution
on `forest1`; the 2026-07-17 request to execute DB02 authorized its named
bounded read-only `wepp3` identity/reachability follow-on. Production mutation
was not authorized and did not occur. The user's 2026-07-17 “commit and push”
request separately authorizes committing this package with the coherent
DB02/DB03 change set and pushing the current
`agent/database-backup-deployment-spec` branch to `origin`; it does not
authorize a PR, merge, or direct push to `main`.

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
- render and exercise the contract in isolated `forest1` fixtures;
- freeze exact production runtime, principal, listener, observed firewall,
  checkout, image, container, network, and volume identities read-only; and
- derive an exact fail-closed DB03 adoption boundary from those identities.

Excluded:

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
- Production observed state: frozen read-only on 2026-07-17 in
  `artifacts/wepp3-production-identity-evidence.md`.

## Assumptions and decisions

- Canonical checkout target: `/workdir/utility-watershed-analytics`.
- Canonical Compose file: `compose.prod.yml`.
- Canonical final project target: `utility-watershed-analytics`. DB03 must
  reconcile this with the observed running project without database recreate.
- Exact PostGIS image:
  `postgis/postgis@sha256:8896823da46b01b1ab5d3eaa9f29712e6bd8d00a7be965f5747fedbfd28d00c9`,
  frozen from the running image without pulling or upgrading it. No fallback
  tag is allowed in production Compose.
- Frozen current project is `utility-watershed-analytics`; `postgis` labels
  point to the canonical checkout while server/Caddy labels point to the
  Actions checkout. DB03 must reconcile only application services.
- Frozen database container ID begins `d2f0c406`, image ID begins `612b68f8`,
  and anonymous-volume ID begins `be7d3b8f`. DB03 must refresh and match the
  complete recorded identities immediately before any action.
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
3. Render and exercise no-recreate, socket, unit, and cancellation gates.
4. Freeze production identities and reconcile DB03 adoption.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit: `agent/database-backup-deployment-spec` at
  `30a9077d432a5c8582759b614e0ea7224713b685`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: `origin/agent/database-backup-deployment-spec`, authorized by
  the user on 2026-07-17
- Pull-request target: do not open a PR
- Authorized systems: repository working tree and disposable non-production
  processes, files, networks, and containers on `forest1`; bounded read-only
  inspection and reachability probes against `wepp3`
- Mutation boundary: repository files and disposable DB02 fixtures; running
  development database/API services and unrelated shared workloads must not be
  stopped or reconfigured; `wepp3` is read-only
- Executor and review assignments: Codex authors, validates, and performs the
  bounded production read; operator retains DB03 mutation authority

## Gates

Always:

- `git diff --check`
- Package diff reviewed against included and excluded scope.

Applicable checks:

- ShellCheck, syntax, safe lock fixtures, nested invocation, contention,
  cancellation, and stale descriptor rejection;
- Compose production render with the exact frozen production image digest;
- static socket inventory proving only Caddy publishes production host ports;
- no-recreate identity preflight against an isolated labeled fixture;
- `systemd-analyze verify`, start/stop/reload fixture behavior, and explicit
  proof no command contains `down` or database stop/remove;
- workflow/YAML and minimized environment handling review;
- host lock boot recreation through tmpfiles static verification;
- read-only exact production identity, principal, listener, checkout, network,
  mount, health, and observed firewall/reachability freeze.

Deferred DB03 mutation gates:

- actual operator/systemd/CI runner group provisioning and contention;
- canonical lock boot recreation on `wepp3`;
- production unit activation, start/stop/reload, cancellation, reboot, and
  application-only rollback; and
- post-adoption reachability and before/after database identity preservation.

These are not DB02 completion gates because the roadmap boundary assigns
repository contract creation to DB02 and production adoption to DB03. The
original scaffold's broader wording is clarified here after the production
freeze exposed the exact adoption mutations required.

## Exit criteria

`EXECUTED-COMPLETE` requires:

- current production PostGIS image is frozen exactly without upgrade;
- current checkout/project/container/image/network/volume/unit/principal and
  listener identities are frozen without mutation;
- current reachability is tested from Compose, localhost, Tailscale, and public
  interfaces and host-firewall behavior is recorded;
- target rendering removes internal host publications and a safe interim DB03
  adoption/rollback boundary is derived from frozen identities;
- the shared/exclusive/inherited lock contract passes isolated nested,
  cancellation, stale-descriptor, and contention tests;
- unit and deployment commands fail closed on database creation/replacement,
  use no build/pull/recreate path, and never contain `down` or database stop;
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
| Exact production identity and principal freeze | `wepp3`, 2026-07-17 | Ran, read-only | Frozen database/container/image/digest/version/project/config/network/anonymous-volume, split checkout labels, unit absence/source, operator/runner identities, environment metadata, and serving health. |
| Localhost, Tailscale, public, and Compose-peer reachability | `wepp3` and `forest1`, 2026-07-17 | Ran, read-only | Current 80/443/5432/8000 host publication confirmed; public blocks 5432/8000, Tailscale reaches them, and both Compose peer paths passed. Exact UFW text was root-only; enabled/active state and externally observed behavior are recorded. |
| `scripts/tests/test_start_runtime.sh` and exact-digest target render | disposable `forest1` files/processes | Ran | Existing database path passed; missing database and proposed `postgis` creation failed closed; target publishes only Caddy and forbids build/pull/recreate. |
| Production unit activation, lock provisioning, reboot, and rollback | `wepp3` | Not run | Production mutation was not authorized and belongs to DB03, not the DB02 contract boundary. |

### Findings and deviations

- Production is one Compose project with split configuration origins: database
  labels point to the canonical checkout, while server/Caddy labels point to
  the Actions runner checkout. DB03 must reconcile application services only.
- The production database still has an anonymous volume. Removing its 5432
  host publication by database recreation is prohibited until DB05; DB03 must
  preserve the observed firewall denial outside approved paths.
- The registered legacy unit is `not-found`, but its unsafe source remains in
  the checkout and contains `compose down`. DB03 must install only the tracked
  safe unit and must not reboot beforehand.
- `--no-recreate` alone permits creation when `postgis` is missing. The new
  runtime-start wrapper asserts identity before action and rejects a dry-run
  database create/replacement before invoking Compose.
- `systemd-analyze verify` rejected the initially proposed
  `ConditionPathIsRegular`. It was replaced with a valid `ConditionPathExists`
  plus an executable owner/mode/symlink/key/digest runtime check.
- A tmpfiles create rehearsal could not apply root/group ownership as the
  development user and was retained as Static syntax/contract evidence only.
- Exact UFW rule text required root and was not read; enabled/active state plus
  the four-source observed reachability matrix is the recorded DB02 evidence.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: repository target, lock, environment, Compose,
  systemd, workflow, identity guard, socket render, app-only dry-run, exact
  production identity, current reachability, and fail-closed DB03 adoption
  boundary passed without production mutation.
- Successor package: DB03 requires explicit production mutation authority. It
  must provision the canonical lock/runtime/unit, reconcile only application
  services, preserve the exact anonymous-volume database, prove actual
  cross-principal behavior, and run the post-adoption backup cycle. DB04 is now
  unblocked for repository implementation; production deployment follows DB03.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
