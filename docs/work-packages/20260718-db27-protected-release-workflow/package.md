# DB27 — Protected release workflow, roles, and status

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB27`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic immutable release
requests/reports/inventory snapshots, fake GitHub event and role fixtures,
workflow/static validation, disposable status fixtures, containers, and local
forest1 rehearsals. It excludes GitHub environment/secret/branch-setting
mutation, workflow dispatch, artifact publication, `wepp3`, production
secrets/data/releases, production unit installation/start, activation,
rollback, commit, push, PR, and other external mutation.

## Objective

Provide a simple protected path from validated immutable release inputs to the
DB26 durable unit, keep preparation/deployment/rollback authority visibly
separate, publish sanitized durable results, and report active-release,
inventory, storage, artifact, backup, and failed/abandoned-attempt health
without making a merge deploy data.

## Decisions

- Use a preparation workflow that reuses data-contract and clean-build CI,
  creates one checksum-bound release bundle, and cannot access a production
  environment or runner.
- Use distinct manual-only deploy and rollback workflows. Both share DB25's
  production concurrency group, but use different GitHub environments and
  invoke DB26's systemd unit rather than owning data mutations.
- Treat the environment reviewer as approver and the self-hosted service/root
  unit as deployer. In this single-operator project one person may perform the
  sequential roles, but no workflow step may collapse or bypass them.
- Bind review to preparation run ID, bundle name, operation ID, action, and
  exact authorization SHA-256 displayed as protected-job inputs.
- Expose only aggregate active-release coordinates through the public API.
  Keep attempts, capacity, paths, and backup ages in the private operator
  monitor/report.
- Use a scheduled/manual read-only status workflow and a deterministic monitor
  over bounded JSON snapshots plus DB26 private state. Workflow failure is the
  current single-operator alert; no paid provider or new service is introduced.

## Gates

- `git diff --check`, Ruff, migration drift, focused server tests, shell/Python
  syntax, workflow/static policy validation, and exact-image regression.
- Bundle creation is deterministic; mutable/symlink/wrong-hash/missing reports,
  unsafe paths, wrong action, and coordinate drift fail closed.
- Preparation has no production environment/runner/secrets. Deploy and rollback
  are manual-only, distinct, environment-protected, digest-bound, serialized,
  and cannot be triggered by merge/push.
- Unauthorized, unapproved, wrong-role, wrong-artifact, mutable-input, and
  deploy-via-rollback-path fixtures fail before systemd start.
- Active API status exactly matches the ledger for EMPTY and ACTIVE states and
  contains no attempt, credential, filesystem, or backup detail.
- Monitor proves healthy, active mismatch, inventory mismatch, low capacity,
  excessive growth, stale artifact, stale backup, failed attempt, abandoned
  attempt, malformed input, and sanitized durable report behavior.
- Failed deploy/status jobs retain sanitized reports as GitHub artifacts; no
  secret or row-level data enters summaries or artifacts.
- Documentation, environment-setting checklist, scope, links, and disposable
  cleanup.

## Execution record

- Added deterministic deploy/rollback authorization bundles that bind the
  exact operation, source commit, request, release/member documents,
  forward/inverse plans, clean-build result, inventory, and every SHA-256.
  Verification rejects wrong actions/roles, commits, operations, hashes,
  filenames, extra/missing members, symlinks, writable files, secret-shaped
  content, and post-preparation mutation.
- Added preparation, deployment, rollback, and status workflows. Preparation
  runs reusable contract/clean-build CI without a production environment,
  secret, or self-hosted runner. Deploy and rollback are distinct manual-only
  protected jobs, share DB25 serialization, verify before install, resume only
  identical installed coordinates, invoke DB26's unit, and retain reports on
  failure. No merge/push path invokes DB26.
- Extended CI so DB27 workflow policy, authorization, status, and DB25
  serialization tests run when these controls change.
- Added the public no-store active-release endpoint with exact EMPTY/ACTIVE
  ledger coordinates and aggregate counts only. It exposes no attempts,
  failures, leases, storage, backup, runner, or credential detail.
- Added private deterministic monitoring for active/inventory mismatch,
  capacity, growth, artifact/backup age, failed and abandoned attempts, strict
  private modes, malformed inputs, and secret-shaped content. Added forest1
  snapshot examples and a scheduled/manual read-only status workflow.
- Passed synthetic preparation/deploy/rollback role and permission rehearsals,
  workflow bypass mutations, healthy/failing monitor fixtures, exact-image
  focused tests, and the complete final-image server regression. GitHub
  environments/settings remain an explicit later administrative task.
- Used synthetic public coordinates and disposable PostGIS only. No workflow
  was dispatched; no artifact was uploaded; no GitHub setting, `wepp3`,
  production secret/release/unit/database, commit, push, PR, or other external
  system was touched during DB27 execution.

### Commands and evidence

| Gate | Result |
| --- | --- |
| Authorization/workflow/status tests | 8 tests passed in 2.073 seconds; deterministic deploy/rollback, wrong role/action/hash/operation/commit, mutation, symlink, secret, workflow-trigger/environment bypass, healthy monitor, six health failures, failed/abandoned attempts, and malformed/private-mode failures covered |
| Workflow policy | Passed distinct `production-data-deploy` / `production-data-rollback`, shared `utility-watershed-analytics-production`, no merge data deployment, preparation isolation, report retention, and read-only scheduled status checks |
| Workflow syntax | All workflow YAML parsed; DB25 serialization validator included all three production workflow environments |
| Final production server image | Built `sha256:1b6c0b59dbe7f7b31ea23a861e646e9b4717d9b6c1c338ce9654361e558b359f`; Ruff and migration drift passed; all 208 tests passed in 92.325 seconds with one expected DB09 schema skip |
| Disposable database | Pinned PostGIS `sha256:4e8c30197f7ce4190cf11a1b8c44bea35a58507558cffa48570814beba77b099`; network/container removed after validation |
| Production boundary | No workflow dispatch/artifact publication/GitHub setting, `wepp3`, production secret/release/unit/database, activation, rollback, or external mutation |

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met with Mixed evidence
- Blocker: none for repository completion; GitHub environments, runner
  permissions, status snapshot collection, and production installation remain
  separately authorized administrative/DB27A work
- First follow-on action: scaffold DB27A compatibility rollout and stop before
  any production schema/code authority
- Successor package: DB27A, not yet scaffolded

## Artifacts

- `artifacts/db27-validation-evidence.md`
- `docs/runbooks/protected-database-release.md`

## Closeout checklist

- [x] Package status/evidence mode are accurate.
- [x] Gates and skipped reasons are recorded.
- [x] Evidence contains no credentials, real coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match authority.
