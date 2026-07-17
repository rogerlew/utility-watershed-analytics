# DB03 — Production runtime convergence

Status: `EXECUTED-HOLD-PUBLISH`

Date: 2026-07-16

Roadmap item: `DB03`

Evidence mode: Mixed

Execution authorization: User-authorized scaffold and execution on 2026-07-17.
This authorizes DB03's bounded read refresh and recorded production runtime,
lock, protected-file, safe-unit, application-only socket convergence,
rollback, and post-adoption backup mutations on `wepp3`. Database identity,
project, image, mount, data, named-volume work, reboot, commit, and push remain
excluded from the host operation. The user's later 2026-07-17 “commit and
push” request separately authorizes committing the coherent DB02/DB03 working
tree and pushing the current `agent/database-backup-deployment-spec` branch to
`origin`; it does not authorize a PR, merge, direct push to `main`, or runner
reenable.

## Objective

Adopt the reviewed interim production runtime safety controls on `wepp3`
without installing or invoking the unsafe legacy unit source, changing the
Compose project, or recreating, replacing, stopping, detaching, or remounting
PostgreSQL.

## Scope

Included:

- refresh the DB02-frozen checkout, unit, Compose, container, image, network,
  listener, principal, and anonymous-volume identities read-only;
- derive and review exact interim actions against those identities;
- prove the legacy registration remains absent and install only the canonical
  safe unit;
- provision and exercise the canonical cross-principal lock;
- install the minimized protected runtime environment and harden sockets using
  actions proven not to recreate the database;
- update only application-facing services and verify identity, reachability,
  smoke tests, rollback, and a scheduled off-host backup cycle;
- remove the obsolete port-8000 firewall allowance; and
- prevent the old lock-bypassing runner workflow from undoing the accepted
  state until the safe workflow is separately committed and pushed.

Excluded:

- changing the Compose project or final checkout identity before DB05;
- adding or migrating to the named PostgreSQL volume;
- upgrading PostgreSQL/PostGIS;
- legacy data reload or watershed release mutation;
- deleting the anonymous source volume.
- committing or pushing repository changes, or rebooting the host.

## Authority and inputs

- Dependencies: DB01 and DB02 `EXECUTED-COMPLETE`.
- Governing files: `docs/ROADMAP.md`,
  `docs/runbooks/production-runtime.md`, and
  `docs/runbooks/database-backup-restore.md`.
- Required frozen inputs: exact current unit text and loaded properties,
  checkout/ref, Compose project/config hashes, containers, images/repository
  digests, networks, listeners, firewall assumptions, principals/groups, and
  PostgreSQL data mount/volume ID.
- Starting production snapshot:
  `../20260716-db02-production-runtime-bundle/artifacts/wepp3-production-identity-evidence.md`;
  refresh every invariant at authorization review and do not reuse the DB02
  development fixture as production evidence.
- Starting repository revision:
  `61e1667e91986d3fba75155f6b473a200fa74141` plus preserved local DB02
  completion changes.

## Assumptions and decisions

- The 2026-07-17 DB03 request records distinct production mutation authority
  within this package's exact boundary.
- DB02 completed the first read-only identity freeze. DB03 refreshes it and
  reviews exact actions and rollback before crossing the mutation boundary.
- Any planned database action, project switch, mount change, or unsafe loaded
  stop invocation is a terminal hold.

## Plan

1. Refresh identities and render an exact no-recreate interim proposal.
2. Review backup freshness, rollback, lock principals, and socket matrix.
3. Install safe controls and update application services only.
4. Verify identity/rollback/backup and reconcile the runtime record.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit: `agent/database-backup-deployment-spec` at
  `61e1667e91986d3fba75155f6b473a200fa74141` plus preserved DB02 changes
- Working branch: `agent/database-backup-deployment-spec`
- Push target: `origin/agent/database-backup-deployment-spec`, separately
  authorized by the user on 2026-07-17
- Pull-request target: do not open a PR unless separately authorized
- Authorized systems: repository/isolated validation on `forest1`; bounded
  DB03 read and mutation on `wepp3`
- Mutation boundary: exact reviewed unit/runtime/lock/application services;
  database container/image/project/mount/volume are invariants
- Executor and review assignments: Codex executes and records; `roger` is the
  operator and rollback owner for this single-operator public-data service

## Gates

- `git diff --check` and package-scope review.
- DB01 current off-host snapshot and restore qualification.
- Refresh DB02 exact image/project/unit/volume and reachability freeze.
- Compose action inspection with zero database actions.
- Cross-principal shared/exclusive/nested/contention/cancellation tests.
- Before/after database identity and listener matrix.
- Application/admin/API smoke and exercised application-only rollback.
- Successful scheduled off-host backup under the adopted lock.

Execution gate note:

- Every mutation remains conditional on the refreshed exact identity, reviewed
  no-database-action plan, and immediately available application-only rollback.
- Reboot was explicitly excluded. Safe-unit start/reload/stop/start and enabled
  state passed, but no reboot-persistence claim is made.
- Runner reenable is skipped because the checked-out workflow is unsafe; the
  disabled state is the fail-closed result until separate publication authority.

## Exit criteria

`EXECUTED-COMPLETE` requires every included mutation and proof above, preserved
sanitized evidence, and no database identity change.

Legitimate holds:

- `EXECUTED-HOLD-DEPENDENCIES`: a future prerequisite regresses or becomes
  invalid. First action: restore the exact prerequisite without weakening exit
  criteria.
- `EXECUTED-HOLD-RECREATE-RISK`: proposal touches database identity. First
  action: preserve production and revise the interim plan; do not apply.
- `EXECUTED-HOLD-AUTHORITY`: exact read or mutation authority absent. First
  action: obtain bounded authority against the reviewed commands.
- `EXECUTED-HOLD-PUBLISH`: host convergence passes, but the connected runner's
  branch lacks the safe workflow and commit/push are unauthorized. First
  action: keep the runner disabled, publish the reviewed repository changes
  under separate authority, verify the checked-out workflow, then reenable it.

## Risks and recovery

- Risk: unsafe checkout unit or old runner workflow bypasses the safe runtime.
  - Prevention: install only the reviewed `/etc` unit; keep the old runner
    disabled until the safe workflow is published and verified.
  - Recovery or rollback: preserve database identities, disable the unsafe
    dispatch path, and restore application-only behavior under the lock.
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
| Scaffold reconciliation | repository and DB02 evidence | Static | DB01/DB02 dependencies and the initial read-only freeze are complete; execution was not yet authorized at scaffold time. |
| Authorized DB03 preflight | `wepp3`, 2026-07-17 | Ran, read-only | Exact database/runtime/checkout/principal/backup/health invariants match DB02, but `sudo -n` is unavailable. The package stopped before mutation. |
| Privilege resume and exact action review | `wepp3` / `forest1` | Ran / Static | Temporary validated sudo restored. Exact digest mapped to the running image; target and rollback dry runs named only server/Caddy actions. Versioned unit/action artifacts were frozen before mutation. |
| Lock, protected runtime, identity, and unit installation | `wepp3` | Ran | `uwa-operators`, tmpfiles, canonical lock, 13-key root mode-`0600` runtime, protected database identity, versioned scripts, interim Compose file, and safe unit installed. Duplicate legacy environment keys were hash-equal and deterministically deduplicated after the first strict check failed closed. |
| Cross-principal lock proof | `wepp3` | Ran | Actual `roger`/`gha` exclusive contention, concurrent shared, TERM 143, and reacquisition passed; refreshed runner/user-manager contexts inherited the group. |
| Application target, rollback, and target reapply | `wepp3` | Ran | Each dry run named only server/Caddy. Application-only target, old-path rollback, and final target passed health with exact database identity unchanged throughout. |
| Firewall and safe unit behavior | `wepp3` | Ran | Obsolete IPv4/IPv6 UFW 8000 allows removed. Safe unit enabled; start/reload/application-only stop/start passed while PostgreSQL remained running and unchanged. |
| Canonical locked off-host backup | `wepp3` / `forest1` | Ran | First valid snapshot exposed a legacy user-lock override. After removing only that override, live descriptor and contention proved the canonical shared lock; snapshot `4361efe3...` published, freshness passed, and `forest1` listed it. |
| Final identity, socket, environment, health, and CI review | `wepp3` / `forest1` | Ran | Database invariant and size passed; port 8000 closed on all tested paths; public/canonical smoke passed. The old remote workflow bypasses the lock, so the idle runner was disabled and legacy `.env` protected mode `0600`. Temporary sudo was removed. |

### Findings and deviations

- DB02 found the legacy unit registration `not-found`; only its unsafe source
  remains. DB03 must preserve absence until it installs the safe tracked unit.
- DB02 found one project with split checkout labels and an anonymous database
  volume. DB03 may reconcile only server/Caddy and must not recreate the
  database to remove port 5432.
- Initial privilege absence caused the first honest hold. After the operator
  restored temporary validated sudo, the package resumed from a fresh exact
  invariant check and completed every authorized host mutation.
- The runtime source repeated required keys; hash-only comparison proved each
  duplicate identical. Strict validation failed first, then the protected file
  was rebuilt with one value per key and passed.
- DB01's backup environment overrode the wrapper's canonical default with a
  user-local lock. The first backup remained valid but was not counted as lock
  proof. Removing only the override made the second live backup descriptor and
  contention test prove the canonical shared lock.
- PostgreSQL port 5432 remains host-published and reachable from localhost and
  the operator Tailscale because removing it would recreate the protected
  anonymous-volume database. Public access is blocked; DB05 owns removal.
- The connected runner checkout still contains the old workflow that bypasses
  the lock and can re-expose port 8000. It was idle, stopped, and disabled; safe
  publication requires separate commit/push authority.

### Terminal disposition

- Final status: `EXECUTED-HOLD-PUBLISH`
- Exit criteria disposition: all authorized host convergence, identity,
  rollback, socket, safe-unit, lock, backup, freshness, and health gates passed.
  Completion is withheld because the safe workflow is not published to the
  connected runner branch and the runner is intentionally disabled.
- Blocker, if held: the separately authorized push publishes only the current
  agent branch; remote `main` still contains the old lock-bypassing deployment
  workflow.
- First follow-on action, if held: review and merge the published agent branch
  into `main` under separate authority, verify the runner checkout uses
  `scripts/deploy_application.sh`, then temporarily restore sudo only long
  enough to enable/start and verify the runner. Do not reenable the old path.
- Successor package: DB03A production runner ownership closure; DB05 follows
  DB04 after DB03A completes

## Successor closure

DB03A reached `EXECUTED-COMPLETE` on 2026-07-17. The safe workflow is on the
fork's `main`, the new fork-owned `wepp3` runner is online and idle, and the old
upstream-owned local runner remains disabled. This resolves DB03's historical
publication hold without rewriting its terminal execution record.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
