# DB05 — Named PostgreSQL volume cutover

Status: `SCAFFOLDED`

Date: 2026-07-16

Roadmap item: `DB05`

Evidence mode: Mixed

Execution authorization: Not authorized. DB01 and DB03/DB03A are complete;
DB04, rehearsal, and production cutover authority remain outstanding.

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
- Starting revision: freeze at authorization review.

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
- Starting branch or commit: freeze after dependencies complete
- Working branch: assign at authorization review
- Push target: do not push unless separately authorized
- Pull-request target: do not open a PR unless separately authorized
- Authorized systems: none until separate rehearsal and production approvals
- Mutation boundary: exact named target and reviewed application/unit switch;
  source volume is read/hold/rollback only and may not be deleted
- Executor and review assignments: named operator, independent approver,
  rollback operator, and recovery owner required

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

Skipped gate and reason:

- All execution: dependencies and authority are absent.

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
| Scaffold review | repository only | Static | DB01 and DB03/DB03A complete; blocked on DB04, rehearsal, and authority. |

### Findings and deviations

- None; execution has not started.

### Terminal disposition

- Final status: pending dependencies and authorization
- Exit criteria disposition: not executed
- Blocker, if held: DB04 incomplete; no rehearsal or production authority
- First follow-on action, if held: complete dependencies and authorize a
  production-shaped cutover/rollback rehearsal
- Successor package, if any: DB05A after rollback window and post-cutover
  restore acceptance

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [ ] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
