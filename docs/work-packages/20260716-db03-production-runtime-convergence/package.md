# DB03 — Production runtime convergence

Status: `SCAFFOLDED`

Date: 2026-07-16

Roadmap item: `DB03`

Evidence mode: Mixed

Execution authorization: Not authorized. DB01 and DB02 are incomplete holds;
production read and mutation authority have not been granted.

## Objective

Adopt the reviewed interim production runtime safety controls on `wepp3`
without invoking the loaded legacy stop path, changing the Compose project, or
recreating, replacing, stopping, detaching, or remounting PostgreSQL.

## Scope

Included:

- freeze current checkout, unit, Compose, container, image, network, listener,
  principal, and anonymous-volume identities under read authority;
- derive and review exact interim actions against those identities;
- neutralize unsafe loaded `ExecStop` without triggering it;
- provision and exercise the canonical cross-principal lock;
- install the minimized protected runtime environment and harden sockets using
  actions proven not to recreate the database;
- update only application-facing services and verify identity, reachability,
  smoke tests, rollback, and a scheduled off-host backup cycle.

Excluded:

- changing the Compose project or final checkout identity before DB05;
- adding or migrating to the named PostgreSQL volume;
- upgrading PostgreSQL/PostGIS;
- legacy data reload or watershed release mutation;
- deleting the anonymous source volume.

## Authority and inputs

- Dependencies: DB01 and DB02 `EXECUTED-COMPLETE`.
- Governing files: `docs/ROADMAP.md`,
  `docs/runbooks/production-runtime.md`, and
  `docs/runbooks/database-backup-restore.md`.
- Required frozen inputs: exact current unit text and loaded properties,
  checkout/ref, Compose project/config hashes, containers, images/repository
  digests, networks, listeners, firewall assumptions, principals/groups, and
  PostgreSQL data mount/volume ID.
- Starting revision and production snapshot: freeze at authorization review;
  do not reuse the DB02 development fixture.

## Assumptions and decisions

- No production command runs until DB01/DB02 completion and distinct read and
  mutation authority are recorded.
- The first production phase is read-only identity freeze. Mutation authority
  is reviewed against its resulting exact action and rollback report.
- Any planned database action, project switch, mount change, or unsafe loaded
  stop invocation is a terminal hold.

## Plan

1. Freeze identities and render an exact no-recreate interim proposal.
2. Review backup freshness, rollback, lock principals, and socket matrix.
3. Neutralize unsafe stop, adopt controls, and update application services only.
4. Verify identity/rollback/backup and reconcile the runtime record.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit: freeze when dependencies complete
- Working branch: assign at authorization review
- Push target: do not push unless separately authorized
- Pull-request target: do not open a PR unless separately authorized
- Authorized systems: none until reviewed; eventual target is `wepp3`
- Mutation boundary: exact reviewed unit/runtime/lock/application services;
  database container/image/project/mount/volume are invariants
- Executor and review assignments: operator, independent reviewer, and incident
  rollback owner must be named before mutation

## Gates

- `git diff --check` and package-scope review.
- DB01 current off-host snapshot and restore qualification.
- DB02 exact image/project/unit/volume and reachability freeze.
- Compose action inspection with zero database actions.
- Cross-principal shared/exclusive/nested/contention/cancellation tests.
- Before/after database identity and listener matrix.
- Application/admin/API smoke and exercised application-only rollback.
- Successful scheduled off-host backup under the adopted lock.

Skipped gate and reason:

- All execution gates: dependencies and production authority are absent.

## Exit criteria

`EXECUTED-COMPLETE` requires every included mutation and proof above, preserved
sanitized evidence, and no database identity change.

Legitimate holds:

- `EXECUTED-HOLD-DEPENDENCIES`: DB01/DB02 incomplete. First action: close their
  exact holds without weakening exit criteria.
- `EXECUTED-HOLD-RECREATE-RISK`: proposal touches database identity. First
  action: preserve production and revise the interim plan; do not apply.
- `EXECUTED-HOLD-AUTHORITY`: exact read or mutation authority absent. First
  action: obtain bounded authority against the reviewed commands.

## Risks and recovery

- Risk: loaded legacy `ExecStop` invokes `down`.
  - Prevention: capture and neutralize it without stop/restart first.
  - Recovery or rollback: preserve database identities, keep the unit inactive,
    and restore application-only behavior under the lock.
- Risk: project/socket hardening proposes database recreate.
  - Prevention: exact action/config-hash and identity guard.
  - Recovery or rollback: do not execute; retain current runtime.

## Artifacts

- `artifacts/` — identity freeze, action plan, authority, lock/socket tests,
  before/after report, rollback, smoke, and backup cycle.

## Execution record

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Scaffold review | repository only | Static | Blocked on DB01, DB02, and production authority. |

### Findings and deviations

- None; execution has not started.

### Terminal disposition

- Final status: pending authorization
- Exit criteria disposition: not executed
- Blocker, if held: DB01/DB02 incomplete; production unauthorized
- First follow-on action, if held: close DB01 decisions and authorize DB02
  read-only identity freeze
- Successor package, if any: DB05 after DB04

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [ ] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
