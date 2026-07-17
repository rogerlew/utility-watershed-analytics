# DB01 — Backup and restore baseline

Status: `EXECUTED-COMPLETE`

Date: 2026-07-16

Roadmap item: `DB01`

Evidence mode: Mixed

Execution authorization: User-authorized Wave 0 orchestration on 2026-07-16,
initially limited to repository mutation and non-production execution on
`forest1`. The operator later authorized a bounded `wepp3` backup and
`forest1` isolated restore drill. That supplemental authority allowed
production database reads and protected task staging but no serving database,
service, deployment, scheduler, or configuration mutation. The operator then
authorized every remaining DB01 backup task except the reboot. That authority
allowed restricted transport and backup-only user configuration/units on
`wepp3`, timer activation, scheduled success/failure/freshness proof, an
isolated `forest1` restore, and cleanup without changing the serving stack. On
2026-07-17 the operator performed the reserved reboot after an apt upgrade and
authorized post-reboot verification. When the upgrade exposed a legacy runtime
failure, the operator temporarily enabled sudo for a bounded parser correction
and no-recreate recovery of the exact existing production containers.

## Objective

Create the repository-owned backup and restore baseline required before any
production runtime or data mutation: verified logical backups, encryption and
off-host transport, scheduled execution and failure reporting, explicit
retention, isolated restore testing, and recovery runbooks.

## Scope

Included:

- harden the existing logical backup command and its evidence contract;
- add encrypted off-host backup orchestration;
- add daily scheduled backup and periodic isolated restore-test units;
- add daily/weekly and explicit release-point retention controls;
- add failure notification hooks and stale-backup monitoring;
- add isolated restore tooling and development fixtures;
- document maintenance, disaster restore, selective restore, role recreation,
  operational-account seeding, key recovery, retention, and failure response;
- execute safe repository gates and isolated `forest1` backup/restore tests;
- execute one bounded representative `wepp3` backup, encrypted transfer, and
  isolated production-shaped restore on `forest1`;
- install and exercise the permanent restricted production transport and
  backup-only user scheduler without rebooting or changing the serving stack;
- verify backup timer, freshness, and encrypted snapshot persistence after the
  operator reboot, then restore serving health without recreating production
  containers or changing database data, image, or volume.

Excluded:

- writing or restoring the serving `wepp3` database;
- recreating or replacing production containers, images, or volumes;
- an agent-initiated reboot of either host;
- changing the production Compose project or PostgreSQL volume;
- implementing DB02 runtime convergence or DB03–DB05 production operations.

## Authority and inputs

- Governing specification: `docs/database-deployment-architecture.md`,
  especially sections 16.4, 17.4, 19.1, 19.4, and 20.
- Governing roadmap: `docs/ROADMAP.md`, Wave 0, DB01.
- Review closure: `docs/database-deployment-roadmap-review.md`, findings O4,
  O6, O7, and closure-pass operational-account requirement.
- Starting repository revision:
  `30a9077d432a5c8582759b614e0ea7224713b685` plus preserved local Wave 0
  readiness and environment-boundary authoring changes.
- Observed development state: `docs/wave-0-readiness.md`.
- Frozen external inputs: the operator selected
  `forest1:/wc1/utility-watershed-analytics-db-backups` as the backup
  destination on 2026-07-16. The final no-reboot authority selected a dedicated
  forced-SFTP production identity and user-local systemd installation while
  continuing to exclude serving-runtime mutation.

## Assumptions and decisions

- Provider contract: encrypted `restic` storage at
  `forest1:/wc1/utility-watershed-analytics-db-backups`. This is off-host from
  production `wepp3`; development rehearsals on `forest1` use the same path
  locally and do not claim off-host evidence. The operator accepts that no
  independent object lock or storage administrator has been established.
- Encryption: `restic` repository encryption. The repository password and
  transport credentials are separate protected operator-readable credentials
  and never appear in repository files, command lines, logs, or evidence.
- Key ownership: this is an explicitly accepted single-operator service. The
  project operator, currently the `roger` account owner, controls backup,
  recovery, restore approval, and restore execution. Separation of duties is
  waived unless another maintainer joins the project.
- Restore authority: production restore remains separately authorized and
  requires maintenance mode, write quiescence, exact source and target
  identity, and a reviewed rollback. This package may restore only into an
  isolated disposable target on `forest1`.
- RPO: use the architecture default maximum of 24 hours until a stricter
  product requirement is accepted.
- RTO: 24 hours. Tooling records and enforces the configured maximum. A
  production-shaped drill must still prove that `forest1` has enough capacity.
- Time retention: keep 14 daily and 8 weekly scheduled snapshots by default.
  These defaults are configurable but may not be weakened silently.
- Release retention: keep explicitly identified recovery points for the active
  release plus two rollback releases. Pruning requires the exact retained
  release identifiers and fails closed when fewer than three are provided.
- Alerting: the single operator accepts the systemd journal and failed-unit
  state on the relevant host as the initial alert channel. No external webhook
  is required for this public-data service.
- Data classification: the operator states that the application data is public
  and there are no end-user accounts or PII. Database and restic credentials
  remain secrets even under this lower-impact classification.

## Plan

1. Define backup, restore, retention, notification, and credential contracts.
2. Implement scripts and systemd units with fail-closed safety checks.
3. Execute isolated backup, encryption, restore, failure, and pruning tests.
4. Record evidence, reconcile durable operations docs, and terminalize.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit: `agent/database-backup-deployment-spec` at
  `30a9077d432a5c8582759b614e0ea7224713b685`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository working tree and isolated non-production
  containers, files, and systemd verification on `forest1`
- Mutation boundary: repository files plus disposable backup and restore-test
  artifacts outside the repository; existing unrelated containers and host
  services must not be changed
- Executor and review assignments: Codex authors and validates; the operator
  owns production decisions and later production authorization
- Supplemental drill boundary: read the production database into an exact
  protected task set, transfer and encrypt it on the accepted backup host,
  restore only into an isolated `forest1` target, verify production health, and
  remove task-created plaintext staging; do not change production runtime or
  scheduling
- Supplemental no-reboot boundary: install only the reviewed restricted
  transport, protected backup configuration, immutable bundle, and user units;
  prove backup/freshness/failure/restore gates and cleanup; do not reboot or
  mutate the serving Compose project
- Supplemental post-reboot boundary: inspect the operator's reboot, invoke the
  reviewed freshness service, verify the encrypted snapshot and serving
  invariants, correct only the Compose-parser-invalid comment discovered after
  upgrade, and recover only the exact existing stopped production containers;
  do not start the unsafe legacy unit, recreate containers, or converge DB02

Every derived kickoff prompt must preserve these coordinates and permissions.

## Gates

Always:

- `git diff --check`
- Package diff reviewed against included and excluded scope.

Applicable checks:

- shell syntax and ShellCheck for every changed shell script;
- safe fixture tests for backup publication, encryption, retention, locking,
  notification, stale detection, restore, and cleanup;
- `systemd-analyze verify` for unit and timer files;
- development database backup followed by restore into an isolated compatible
  PostGIS container, with archive checksums, roles, extensions, migrations,
  sequences, table counts/fingerprints, database checks, and API smoke checks;
- documentation links, referenced paths, code fences, and commands;
- production Compose remains render-only; the supplemental production drill
  must not recreate, restart, or reconfigure the serving stack.

Skipped gate and reason: none.

## Exit criteria

`EXECUTED-COMPLETE` requires:

- scheduled encrypted backups reach an accepted off-host repository and stale
  or failed runs notify the accepted operations channel;
- daily/weekly and active-plus-two release retention are exercised safely;
- an isolated production-compatible restore meets an accepted maximum RTO and
  proves the required database and application checks;
- encryption-key recovery, missed timer, forced failure, reboot persistence,
  controlled pruning, maintenance entry/exit, and selective restore are
  exercised and recorded;
- authoritative docs, roadmap, and catalog are reconciled.

Legitimate hold outcomes:

- `EXECUTED-HOLD-OFFHOST-DECISIONS`: repository and isolated development work
  passes, but provider acceptance, named key owners, accepted RTO, or
  production-shaped capacity remains unresolved. First follow-on: record those
  decisions and authorize a bounded off-host staging drill.
- `EXECUTED-HOLD-RESTORE-FAILED`: an isolated restore or required invariant
  fails. First follow-on: preserve sanitized evidence and fix the smallest
  reproducible restore defect before any production mutation.
- `EXECUTED-HOLD-RTO-MISSED`: a correctly provisioned drill exceeds the
  accepted maximum. First follow-on: provision capacity or revise the accepted
  requirement through explicit owner review, then rerun the complete drill.
- `EXECUTED-HOLD-PRODUCTION-DRILL`: provider and operating decisions are closed,
  but the encrypted `wepp3`-to-`forest1` backup and isolated production-shaped
  restore have not been authorized and exercised. First follow-on: authorize
  that bounded drill without changing the serving production stack.
- `EXECUTED-HOLD-PRODUCTION-SCHEDULER`: the representative manual production
  backup and isolated restore pass, but the permanent transport identity,
  production schedule, scheduled failure/stale notification, or reboot
  persistence remain unproved. First follow-on: authorize a bounded
  backup-only installation and reboot drill without changing the serving
  database or Compose project.
- `EXECUTED-HOLD-REBOOT-EVIDENCE`: permanent transport, scheduling,
  success/failure/freshness, isolated restore, and cleanup pass, but the
  operator-reserved reboot and post-reboot persistence checks remain. First
  follow-on: reboot `wepp3`, then verify timers, service results, snapshot
  visibility/freshness, and serving health without changing the stack.

## Risks and recovery

- Risk: backup artifacts or logs expose credentials or role verifiers.
  - Prevention: protected staging and credentials, redacted logs, secret
    scanning, encrypted transport, and no sensitive artifacts in Git.
  - Recovery or rollback: revoke exposed credentials, quarantine the artifact,
    rotate database and transport access, and rerun from a clean target.
- Risk: pruning removes required release recovery points.
  - Prevention: exact release allowlist, minimum-three invariant, dry-run
    report, and separate apply action under the host-wide lock.
  - Recovery or rollback: object-store versioning/object lock and recovery-owner
    credentials restore the deleted snapshot metadata when supported.
- Risk: a restore targets the serving database.
  - Prevention: restore tooling requires an explicit disposable-target label,
    rejects the source container, and never defaults a target.
  - Recovery or rollback: stop immediately, preserve exact identities, keep
    maintenance mode active, and invoke the separately authorized recovery
    procedure.

## Artifacts

- `artifacts/` — sanitized command transcripts, versions, timings, checksums,
  invariant summaries, failure injection, pruning, and review notes.

Do not store secrets, environment files, database dumps, raw restic repository
data, or large source data in the package directory.

## Execution record

Fill this section during execution.

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Wave 0 readiness and package scope review | `forest1`, 2026-07-16 | Mixed | DB01 selected; repository and isolated local execution authorized; production and external provider actions excluded. |
| `scripts/run_scheduled_backup.sh` with disposable encrypted restic repository | `forest1` development database | Ran | Atomic backup, checksum/decode validation, encrypted snapshot publication, 100% fixture repository check, and success-state publication passed. |
| `scripts/run_restore_test.sh` with 120-second development threshold | isolated internal Docker network and disposable PostGIS target | Ran | Exact roles/memberships subset, extensions, migrations, sequences, schema, and 55 table fingerprints passed; Django database/list API smoke passed; achieved 26 seconds. |
| Forced failure, stale check, retention dry-run/apply, and recovery-password copy | disposable local fixtures | Ran | Failed runs did not publish success; stale state failed; fewer than three releases failed; exact three-release retention passed; recovery copy opened and checked the repository. |
| ShellCheck, Ruff, targeted Django tests, shell/Python syntax, and systemd verification | `forest1` and pinned tool containers | Ran | Passed; detailed commands and the one unrelated host-unit warning are recorded in `artifacts/forest1-isolated-evidence.md`. |
| Accepted backup-host setup | `forest1:/wc1/utility-watershed-analytics-db-backups` | Ran | Installed user-local restic 0.16.4, initialized the mode-`0700` encrypted repository, published and verified two development snapshots, passed freshness and 14-daily/8-weekly retention, and restored the newest snapshot with database and Django smoke checks in 25 seconds. |
| User scheduler | `forest1` user systemd manager | Ran | Daily backup, weekly retention, and weekly restore-test timers enabled; backup, retention, and restore-test services passed; user lingering enabled so timers survive logout. |
| Bounded production backup, authenticated SSH pull, restic publication, exact isolated restore, Django smoke, production postcheck, and cleanup | `wepp3` source and `forest1` isolated target, 2026-07-16 | Ran | Non-empty 27.8 GB production database backed up into a 1.21 GB verified archive; encrypted snapshot `d18a3f06085a8aed92fdc1b48949f6dea2578114de169b1dde1730f31213716b` published; every restored table fingerprint/schema check and representative API smoke passed in 387 seconds; production identity, counts, uptime, and public health remained unchanged. See `artifacts/wepp3-forest1-production-drill-evidence.md`. |
| Permanent restricted transport and user-local production installation | `wepp3` to `forest1`, 2026-07-16 | Ran | Dedicated source-restricted forced-SFTP identity, pinned host key, immutable exact-revision bundle, protected configuration/state, restic 0.16.4, and reviewed user units installed and verified. See `artifacts/wepp3-production-scheduler-evidence.md`. |
| Installed production backup and independent snapshot verification | `wepp3` source and `forest1` repository | Ran | Source backup checks passed; direct client-side encrypted publication created scheduled snapshot `1db1e3a475748e86692a26f5da0127e23399a2a2833a715bd68fd11133592359`; independent query and repository verification passed. |
| Normal freshness, planned stale failure, and accepted notification | `wepp3` user systemd manager | Ran | Normal 90,000-second checks passed; an isolated one-second threshold failed, invoked `OnFailure`, and wrote the accepted local journal alert; exact cleanup returned the service to success with no failed units. |
| Installed restore-test service against newest scheduled snapshot | `forest1` isolated target | Ran | Exact schema and every-table comparison plus non-empty Django smoke passed in 376 seconds; disposable resources were removed. |
| Backup/freshness timer activation and no-reboot production postcheck | `wepp3` | Ran | Both timers are enabled and active under the lingering user manager; boot time, serving identities, zero restarts, data counts, checkout, and public health remained unchanged. Reboot was intentionally deferred to the operator. |
| Operator reboot, backup persistence, snapshot verification, bounded serving recovery, and final invariants | `wepp3` and `forest1`, 2026-07-17 | Ran | Both backup timers persisted; post-reboot freshness and independent snapshot access passed. An apt/Compose upgrade exposed an invalid legacy `.env` comment and unsafe boot unit. The exact comment was corrected; the unsafe unit was not started; only the existing database/server containers were started. Image, volume, 27.8 GB database, all three aggregate counts, and HTTP/API health passed. See `artifacts/wepp3-post-reboot-evidence.md`. |

### Findings and deviations

- The operator accepted `forest1:/wc1/utility-watershed-analytics-db-backups`,
  single-operator ownership, a 24-hour RPO and RTO, and local systemd failure
  state as the alert channel. No S3 provider or separate recovery owner is
  required for this public-data service.
- The development database contains no watershed rows because its external seed
  tokens are expired. The restore drill therefore used the explicit
  development-only empty-database allowance and could prove the list endpoint,
  but not representative watershed detail/child reads.
- A `pg_isready`-only target check raced the PostGIS initialization restart.
  The runner now waits for the final initialization-complete log marker before
  readiness; the complete rerun passed.
- The representative production drill proved the accepted 24-hour RTO with a
  387-second full encrypted restore, exact database comparison, and non-empty
  application smoke. It did not change or restart the serving stack.
- `wepp3` could verify `forest1` over Tailscale but lacked accepted outbound SSH
  authentication. The manual drill safely used the existing authenticated
  `forest1` pull path before local restic publication. The later no-reboot task
  installed a dedicated source-restricted forced-SFTP identity and proved
  direct encrypted scheduled publication.
- Non-interactive sudo was unavailable. The backup-only profile was therefore
  installed under the lingering `roger` user, matching the already accepted
  single-operator model. Refreshing only that user's systemd manager supplied
  its existing Docker-group context; no serving container was restarted.
- The first scheduled service attempt safely failed before staging because the
  old lingering user manager lacked the Docker group. `OnFailure` logged the
  accepted journal alert. After the user-manager-only refresh, the retry and
  all later gates passed.
- The first stale-test override was ineffective because the base
  `EnvironmentFile` had later precedence. A runtime-only `ExecStart` override
  supplied the one-second threshold, produced the planned failure and alert,
  and was removed before the normal passing rerun.
- The operator's apt upgrade moved Docker Engine/Compose to 29.6.2/v5.3.1.
  After reboot, the legacy production unit failed because Compose rejected an
  exact `//` line in `.env`. The database shut down cleanly and retained its
  image and volume. Correcting only that comment restored parsing.
- A dry run proved the legacy unit would build, pull, create development
  services, and recreate the existing server. It was not started. The task
  recovered only the exact stopped database and server containers, after which
  counts and public health matched. Runtime convergence and future serving
  reboot persistence remain DB02 work. After verification, the operator used
  plain `systemctl disable`; the linked registration is now `not-found` without
  invoking its unsafe stop action, while the source unit and hash remain
  captured for DB02. The legacy unit is not DB01 backup evidence.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: repository implementation, isolated encrypted
  workflow, exact restore comparison, application smoke framework, failure
  injection, retention, recovery access, accepted provider/owner/RPO/RTO/alert
  decisions, live `forest1` scheduler gates, representative encrypted
  `wepp3` transport, non-empty production-shaped restore, exact comparison,
  application smoke, accepted RTO, permanent restricted production transport,
  installed production scheduling, scheduled success/failure/freshness,
  journal notification, exact scheduled restore, cleanup, operator reboot,
  timer persistence, post-reboot freshness, independent snapshot visibility,
  and final production invariants met.
- Blocker, if held: none.
- First follow-on action, if held: not applicable.
- Successor package, if any: DB02 should use the captured failed legacy boot,
  unsafe Compose dry run, disabled/not-found registration, and preserved source
  unit/hash as production-identity evidence before any runtime mutation. DB03
  and DB05 remain blocked on their other dependencies.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
