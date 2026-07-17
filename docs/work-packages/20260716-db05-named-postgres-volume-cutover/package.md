# DB05 — Named PostgreSQL volume cutover

Status: `EXECUTED-COMPLETE`

Date: 2026-07-16

Roadmap item: `DB05`

Evidence mode: Mixed

Execution authorization: The user first authorized the bounded `forest1`
rehearsal, then on 2026-07-17 explicitly granted the reviewed `wepp3`
production authority and confirmed passwordless sudo. This authorized the
exact preflight, maintenance, backup, cutover, rollback/reapply, runtime
convergence, reboot, post-backup/restore, and temporary-privilege removal in
the authority plan. The user later separately authorized commit/push, producing
agent-branch commit `2c6f426...`. On 2026-07-17 the user then explicitly
authorized the fork `main` fast-forward and completion of the publication
hold. Fork `main` and the clean production checkout were fast-forwarded under
that authority. Source-volume deletion remains excluded for DB05A.

## Objective

Under maintenance and the exclusive host lock, move the exact production
database from its held anonymous source volume to the canonical named volume
using the pinned current image, complete final Compose/systemd convergence,
exercise rollback, and retain the source against ordinary prune.

## Scope

Included:

- freeze exact source container/image/anonymous-volume and target identities;
- create and verify a fresh encrypted off-host backup after write quiescence;
- provision the named target with the same pinned PostgreSQL/PostGIS image;
- restore or use a separately reviewed compatible physical-copy procedure;
- verify roles, memberships, extensions, migrations, sequences, release state,
  schema, watershed/non-watershed counts/fingerprints, and application behavior;
- switch canonical Compose/systemd, exercise rollback, reboot, and scheduled
  post-cutover backup/restore;
- retain the source through a stable prune-resistant exact reference.

Excluded:

- PostgreSQL/PostGIS upgrade;
- deleting the source anonymous volume (DB05A only);
- watershed release activation or legacy loader mutation;
- proceeding without accepted DB01 RTO/capacity or exact rollback.

## Authority and inputs

- Dependencies: DB01, DB03 host convergence plus DB03A closure, and DB04
  `EXECUTED-COMPLETE`.
- Governing files: Wave 0 DB05, architecture sections 19.1/19.4, database
  backup/restore runbook, production runtime runbook, and DB03 identity record.
- Frozen inputs: exact source identities, fresh snapshot ID/hash/age, accepted
  target name, pinned image, maintenance route, RTO, capacity/WAL margin,
  rollback window, operator/approver, and commands.
- Starting revision: `6f46aaf643374047e2b5251fd5c15167c9843c0e`.

## Assumptions and decisions

- Logical restore is the default because it validates recoverability. A
  physical copy requires a separate exact-version procedure and review.
- Source volume receives a stable label/reference before detachment and remains
  excluded from ordinary prune through the rollback window.
- Final project/unit convergence occurs only after the named target passes and
  rollback has actually been exercised.

## Plan

1. Rehearse full cutover/rollback with production-shaped data and accepted RTO.
2. Freeze production identities, enter maintenance, and prove quiescence.
3. Back up, restore/copy, verify, switch, and exercise exact rollback.
4. Reapply accepted target, reboot, post-backup/restore-test, and retain source.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit:
  `6f46aaf643374047e2b5251fd5c15167c9843c0e`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: agent branch and fork `main` published; no force push
- Pull-request target: do not open a PR unless separately authorized
- Authorized systems: repository, isolated `forest1` rehearsal resources,
  encrypted backup repository, and exact DB05 runtime/database/service/checkout
  boundaries on `wepp3`
- Mutation boundary: reviewed maintenance route, fresh backups, exact source
  holder, named target, canonical Compose/unit/identity, reboot, and fork-owned
  checkout convergence; no source deletion, pruning, data reload, or upgrade
- Executor/reviewer/rollback owner: Codex executes and records; `roger` owns
  the single-operator authorization and recovery decision

## Gates

- DB01 fresh encrypted off-host snapshot and accepted restore qualification.
- Production-shaped cutover and actual rollback within RTO.
- Maintenance route and write-quiescence proof.
- Exact source/target/image/volume identities and free-space/WAL preflight.
- Roles, extensions, migrations, sequences, release state, schema, all required
  counts/fingerprints, and application smoke.
- Final application rollback and database source rollback actually exercised.
- Restart and host reboot persistence.
- Post-cutover scheduled backup and isolated restore test.
- Source stable reference and prune prohibition.

Publication gate:

- Separate authority fast-forwarded fork `main`, preserved the obsolete
  interim Compose file as protected evidence, cleanly fast-forwarded the
  canonical production checkout under the exclusive lock, and independently
  verified unchanged runtime and database identity.

## Exit criteria

`EXECUTED-COMPLETE` requires a verified named production volume, exercised
rollback, final canonical runtime, reboot proof, post-cutover backup/restore,
and retained exact source volume.

Legitimate holds:

- `EXECUTED-HOLD-DEPENDENCIES`: any dependency incomplete.
- `EXECUTED-HOLD-QUIESCENCE`: writes cannot be proven stopped.
- `EXECUTED-HOLD-RTO-MISSED`: drill/cutover exceeds accepted RTO.
- `EXECUTED-HOLD-IDENTITY`: source or target identity differs.
- `EXECUTED-HOLD-ROLLBACK`: rollback cannot be exercised exactly.
- `EXECUTED-HOLD-PRODUCTION-AUTHORITY`: the rehearsal passed but production
  access and mutation are not authorized.
- `EXECUTED-HOLD-PUBLISH`: production gates passed and the reviewed commit is
  on the agent branch, but fork `main` and the production checkout cannot yet
  be cleanly fast-forwarded to it.

Each hold preserves both volumes and records one concrete next action. No hold
authorizes deletion or an upgrade.

## Risks and recovery

- Risk: adding the mount starts an empty database.
  - Prevention: provision/verify target before Compose switch and inspect
    actions.
  - Recovery or rollback: point application-only runtime back to the retained
    exact source under maintenance and lock.
- Risk: prune loses the only rollback volume.
  - Prevention: stable label/reference and explicit prune prohibition.
  - Recovery or rollback: use fresh verified off-host backup; terminalize hold.

## Artifacts

- `artifacts/` — authority, identities, maintenance/quiescence, backup,
  timings, inventories, action plans, rollback, reboot, socket/smoke, and
  post-cutover restore evidence.

## Execution record

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Authority and boundary freeze | repository / `forest1` | Static | Starting commit, exact source snapshot/image, 24-hour maximum RTO, protected rehearsal root, task resource prefix, and no-production boundary recorded. |
| Production-shaped source restore | isolated `forest1` | Ran | Snapshot `4361efe3...` restored into an anonymous volume with exact PostgreSQL 17.5/PostGIS 3.5.2 schema, inventories, and table fingerprints in 338 seconds. |
| Maintenance and quiescence | isolated `forest1` | Ran | Internal-only Caddy returned HTTP 503; a bounded observation interval proved zero writers and unchanged inventory. |
| Named-volume cutover and rollback | isolated `forest1` | Ran | Fresh encrypted pre-backup `709abac7...`; named target restore in 358 seconds; cutover 370 seconds, actual source rollback 5 seconds, and target reapply 4 seconds. |
| Persistence and data equality | isolated `forest1` | Ran | Restart and container recreation preserved the named target; pre/post table fingerprints were exact. |
| Post-cutover recovery | isolated `forest1` | Ran | Encrypted post-backup `d90d213e...` restored into a second isolated target in 385 seconds; exact comparisons and production-mode Django/API smoke passed. |
| Cleanup and production hold | `forest1` / repository | Ran / Static | Disposable containers, networks, volumes, and plaintext were removed; development remained healthy; `wepp3`, reboot, GitHub, commit, and push were not accessed or executed. |
| Repository closeout gates | `forest1` | Ran | Shell syntax, production Compose render, lock/runtime tests, relative Markdown links, diff whitespace, literal-secret scan, executable modes, ignored-log boundary, and independent Docker cleanup checks passed. ShellCheck was unavailable. |
| Production identity/capacity preflight | `wepp3` | Ran, read-only | Historical container `d2f0c406...`, image `612b68f8...`, anonymous volume `be7d3b8f...`, versions, health, zero restarts/writers, 580 GiB free, timers, public API, runner, sudo, and exclusive lock matched. |
| Maintenance, quiescence, and pre-backup | `wepp3` / external `forest1` | Ran | Both public domains and representative API returned HTTPS 503; Django stopped; bounded inventory remained exact; 1,212,820,636-byte backup `47e0f0b...` published as encrypted snapshot `cc7236b3...`. |
| Production named-target restore | isolated `wepp3` | Ran | Exact-image restore completed in 388 seconds with verified roles subset, extensions, migrations, sequences, schema, and every table fingerprint. Rehearsal-tested smoke image passed production-mode API checks. |
| Production cutover/rollback/reapply | `wepp3` | Ran | Named cutover 4 seconds, actual anonymous-source rollback 6 seconds, and target reapply 5 seconds passed. Restart, Compose recreation, exact final inventory, and public recovery passed. |
| Runtime/checkout/reboot convergence | `wepp3` | Ran | Safe immutable DB05 bundle/unit and protected named identity installed; checkout ownership moved to `roger`, origin to the fork, branch to `main`; reboot changed boot ID and preserved exact database/container/volume, source holder, services, timers, runner, sockets, and lock. |
| Post-cutover recovery | `wepp3` / isolated `forest1` | Ran | 1,212,259,187-byte backup `da89c44f...` published as snapshot `cb9284c0...`; global-newest restore, exact comparisons, and production-mode smoke passed in 386 seconds. |
| Production closeout | `wepp3` / external `forest1` | Ran | Named database is healthy with no 5432 publication; source holder remains stopped/prune-prohibited; 8000 is not published; public routes return 200; disposable resources/plaintext are absent; temporary passwordless sudo was removed. |
| Final repository/evidence gates | `forest1` / read-only `wepp3` | Ran | Shell syntax, Compose render, lock/runtime tests, links, whitespace, literal-secret scan, local/production Compose SHA equality, ignored-log boundary, final public/identity/resource checks, and development health passed. ShellCheck remained unavailable. |
| Agent-branch publication | repository / GitHub | Ran | Commit `2c6f426...` was pushed to `origin/agent/database-backup-deployment-spec` under separate authority; the remote ref matched exactly and no PR or workflow dispatch was requested. |
| Fork and production publication | GitHub / `wepp3` | Ran | Fork `main` fast-forwarded without force to reviewed commit `d52aae4...`; under the exclusive lock, the exact local Compose delta was reconciled, obsolete `compose.db03.yml` was checksummed and preserved mode `0600`, and the checkout cleanly fast-forwarded. Exact named database/container/image/holder identity, unit/timers/runner, closed ports 5432/8000, and four public checks remained accepted without service restart or workflow dispatch. |

### Findings and deviations

- Four fail-closed attempts exposed and corrected an empty Docker port-binding
  representation, the two-line `restore_smoke` output contract, restored-target
  database selection, and test-mode Silk self-writes. Every failed attempt
  removed its disposable resources before the next attempt.
- The reusable restore smoke now uses the production environment contract and
  validates its final JSON report. Backup defaults remain unchanged, while
  explicit database/user overrides support an isolated restored target.
- The successful run retained only its mode-`0700` encrypted repository and
  sanitized evidence. No production observation was refreshed, so prior DB03
  identities are historical inputs and must match a fresh production freeze.
- Production preflight found two stale rehearsal-time restic locks. Their
  recorded process was absent; `restic unlock` removed only the locks and the
  repository subset check then passed without snapshot/data pruning.
- The historical serving image predates `restore_smoke`. The production
  harness stopped after the target's exact database comparison and before
  source/checkout mutation; the exact rehearsal-tested smoke-only image was
  streamed to `wepp3`, verified by image ID, and the harness resumed from the
  retained target.
- The enabled unit acquired the operations lock late in boot after Docker and
  initially appeared inactive; it completed successfully at 14:14:20. A
  transient 502 during Gunicorn startup also cleared inside bounded readiness.
- The canonical checkout was owned by historical account `brandon`; the first
  remote rename stopped before Git mutation. The checkout was then explicitly
  re-owned by `roger`, moved to fork `main`, and revalidated under the lock.
- Publication preflight initially used an incorrect assumed database container
  name and non-contract public domains, then stopped without mutation. Exact
  Compose labels and the tracked Caddy contract resolved both checks before
  the checkout fast-forward.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: every rehearsal, production, recovery, and
  publication gate passed; fork `main` and the production checkout are cleanly
  converged on the reviewed DB05 history
- Blocker, if held: not applicable
- First follow-on action, if held: not applicable
- Successor package, if any: DB05A after rollback window and post-cutover
  restore acceptance

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
