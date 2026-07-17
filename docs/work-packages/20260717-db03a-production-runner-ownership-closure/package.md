# DB03A — Production runner ownership closure

Status: `EXECUTED-HOLD-PRIVILEGE`

Date: 2026-07-17

Roadmap item: `DB03A`

Evidence mode: Mixed

Execution authorization: The user's 2026-07-17 request to “scaffold and
execute as DB03 closure package,” following explicit agreement to move
production automation to `rogerlew/utility-watershed-analytics`, authorizes
this package's repository, GitHub, and bounded `wepp3` runner mutations.

## Objective

Close DB03's publication hold by fast-forwarding the reviewed safe runtime and
deployment workflow to the fork's `main`, registering a new fork-owned
self-hosted runner on `wepp3`, delivering the existing minimized production
runtime as the fork's protected `PRODUCTION_ENV` secret without exposing its
values, and proving the new runner online and idle while the old upstream-owned
runner remains disabled.

## Scope

Included:

- scaffold and publish this governed successor package;
- fast-forward `rogerlew/utility-watershed-analytics:main` from the reviewed
  `agent/database-backup-deployment-spec` branch;
- verify Actions enablement, the exact `main` workflow, required secret names,
  queued/in-progress runs, and repository administration authority;
- create/update only the fork repository's `PRODUCTION_ENV` Actions secret
  from `/etc/utility-watershed-analytics/runtime.env` through a non-logging
  pipe;
- install a checksum-verified GitHub Actions runner release in a new directory,
  register it only to the `rogerlew` fork with label `deploy`, and install its
  system service as `gha`;
- verify refreshed `uwa-operators` membership, online/idle GitHub state,
  checked-out workflow identity, service enablement, and production runtime/
  database invariants; and
- retain the old upstream runner disabled until its separate deregistration is
  possible and reviewed.

Excluded:

- dispatching the deployment workflow or any other production job;
- changing application, database, container, image, project, network, mount,
  volume, data, firewall, safe runtime unit, backup schedule, or runtime secret
  values;
- rebooting `wepp3`;
- force-pushing or rewriting history;
- changing the upstream `brandonxu360` repository; and
- opening a pull request unless direct fast-forward publication is rejected.

## Authority and inputs

- Predecessor: DB03 `EXECUTED-HOLD-PUBLISH` with every host convergence gate
  passed and the unsafe runner disabled.
- Repository: `rogerlew/utility-watershed-analytics` (fork of
  `brandonxu360/utility-watershed-analytics`), default branch `main`.
- Starting branch revision:
  `3478b6d49148bfda090476022b2f97a6dae08752`.
- Starting `main` revision:
  `28095c7b6620c187dfaa50c4d82d5a9eb2fdd359`.
- `main` is an ancestor of the starting branch, Actions is enabled, the fork
  grants the authenticated `rogerlew` account admin permission, and no fork
  runner, Actions secret, queued run, or in-progress run was observed.
- Production target: `wepp3`; new runner account: `gha`; required runner label:
  `deploy`.

## Decisions

- Use a new runner directory and service. Do not repoint or overwrite the old
  upstream runner installation.
- Pin the new installation to the already-running runner version `2.335.1` and
  verify the official release digest before extraction.
- Do not run the deployment workflow merely to prove registration. GitHub
  online/idle state, exact workflow content on `main`, service state, runner
  labels, and unchanged production runtime are the closure evidence.
- The old upstream registration may remain offline if the authenticated fork
  owner cannot administer the upstream repository. Its local service must stay
  disabled/inactive.

## Plan

1. Publish the governed scaffold and safe branch to fork `main`.
2. Verify exact `main` workflow and configure the protected secret.
3. Install and register the fork-owned runner in a new directory.
4. Verify online/idle state and unchanged production runtime.
5. Close DB03A, reconcile DB03/catalog/roadmap, and publish evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch: `agent/database-backup-deployment-spec`
- Working branch: `agent/database-backup-deployment-spec`
- Push targets: the current branch and fast-forward-only
  `origin/main`, authorized by this closure request
- Pull-request target: none unless fast-forward-only push is rejected
- Authorized systems: local repository, GitHub fork configuration, and bounded
  runner installation/configuration on `wepp3`
- Mutation boundary: repository refs/docs, fork Actions secret/runner
  registration, new runner files/service, and old runner disabled state only
- Executor/reviewer/rollback owner: Codex executes and records; `roger` owns
  single-operator rollback

## Gates

- `git diff --check`, documentation links, and secret-assignment/path scan.
- Fast-forward ancestry and exact remote-ref verification.
- `main` workflow calls `scripts/deploy_application.sh`, uses non-cancelling
  production concurrency, writes a mode-`0600` temporary runtime, and cleans it.
- Fork has exactly one expected production secret name without value exposure.
- Runner archive digest matches official GitHub release metadata.
- New service runs as `gha`, is enabled/active, inherits `uwa-operators`, and
  GitHub reports runner `wepp3` online, idle, with label `deploy`.
- No queued or in-progress run before enablement; no job dispatch by package.
- Old upstream service remains disabled/inactive.
- Exact DB03 database identity, safe runtime unit, backup timers, port 8000
  closure, and public/canonical smoke remain unchanged.
- Temporary passwordless sudo is removed at closeout.

## Exit criteria

`EXECUTED-COMPLETE` requires every gate above, sanitized durable evidence, the
new fork-owned runner online/idle, old local runner disabled, and unchanged
production runtime/database identity.

Legitimate holds:

- `EXECUTED-HOLD-PRIVILEGE`: noninteractive sudo absent. First action:
  temporarily restore validated sudo and resume from fresh invariants.
- `EXECUTED-HOLD-SECRET`: protected runtime unavailable or secret delivery
  fails. First action: leave both runners disabled and repair delivery without
  printing values.
- `EXECUTED-HOLD-RUNNER`: release verification, registration, service, label,
  or GitHub online/idle proof fails. First action: stop/disable only the new
  runner, preserve old disabled state, and diagnose from sanitized logs.
- `EXECUTED-HOLD-PUBLISH`: `main` cannot fast-forward safely. First action:
  leave production unchanged and use a reviewed PR rather than force-push.

## Risks and recovery

- Risk: the new runner accepts an unexpected queued deploy immediately.
  - Prevention: verify no queued/in-progress runs before registration and
    before service start; do not dispatch a workflow.
  - Recovery: stop/disable the new service; exact DB03 runtime remains active.
- Risk: secret content reaches logs or process arguments.
  - Prevention: pipe the protected file directly to `gh secret set`; never
    echo, persist, hash, or log its values.
  - Recovery: stop, rotate the affected secret through the protected delivery
    path, and preserve only sanitized failure evidence.
- Risk: runner swap changes production runtime.
  - Prevention: no workflow dispatch and before/after exact runtime invariants.
  - Recovery: disable new runner; do not touch database/application services.

## Artifacts

- `artifacts/` — sanitized branch/workflow, release, runner, secret-name,
  service, and unchanged-runtime evidence.

## Execution record

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Closure preflight | `forest1` / GitHub | Ran | Fork admin and Actions enabled; `main` fast-forwards to `3478b6d`; no fork secrets, runners, queued/in-progress runs, or branch protection observed. |
| Governed scaffold and safe `main` publication | repository / GitHub | Ran | Scaffold commit `485c275...` pushed to the agent branch and fast-forwarded fork `main` from `28095c7...`; exact safe deploy workflow hash matches and all three workflows are active. No run was created or queued. |
| Runner/repository/production preflight | GitHub / `wepp3` | Ran, read-only | Official runner v2.335.1 asset advertises SHA-256 `4ef2f252...`; fork still has zero secrets/runners/runs. Old runner is disabled/inactive, new path absent, safe runtime/timers/health and exact database identity match. `sudo -n` is unavailable, so execution stopped before secret or runner mutation. |

### Findings and deviations

- GitHub did not list workflows immediately after the first `main` publication
  read, then listed all three active workflows after repository processing;
  no push-triggered run was created.
- Required temporary noninteractive privilege is absent. No fork secret,
  runner registration, production file, or service was changed.

### Terminal disposition

- Final status: `EXECUTED-HOLD-PRIVILEGE`
- Exit criteria disposition: safe fork `main` publication passed; protected
  secret delivery and runner installation/registration remain unexecuted
- Blocker, if held: `roger` lacks noninteractive sudo required to read the
  protected runtime through a non-logging pipe and install the new runner/service
- First follow-on action, if held: temporarily restore validated passwordless
  sudo for `roger`, then resume from a fresh no-runs/runtime invariant check
- Successor package, if any: DB04/DB05 after DB03A completes

## Closeout checklist

- [x] Package status/evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit/push actions match recorded authorization.
