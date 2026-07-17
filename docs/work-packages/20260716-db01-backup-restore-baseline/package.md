# DB01 — Backup and restore baseline

Status: `EXECUTED-HOLD-PRODUCTION-DRILL`

Date: 2026-07-16

Roadmap item: `DB01`

Evidence mode: Mixed

Execution authorization: User-authorized Wave 0 orchestration on 2026-07-16,
limited to repository mutation and non-production execution on `forest1`.
Production access and mutation are not authorized.

## Objective

Create the repository-owned backup and restore baseline required before any
production runtime or data mutation: verified logical backups, encryption and
off-host transport, scheduled execution and failure reporting, explicit
retention, isolated restore testing, and recovery runbooks.

## Scope

Included:

- harden the existing logical backup command and its evidence contract;
- add encrypted S3-compatible off-host backup orchestration;
- add daily scheduled backup and periodic isolated restore-test units;
- add daily/weekly and explicit release-point retention controls;
- add failure notification hooks and stale-backup monitoring;
- add isolated restore tooling and development fixtures;
- document maintenance, disaster restore, selective restore, role recreation,
  operational-account seeding, key recovery, retention, and failure response;
- execute safe repository gates and isolated `forest1` backup/restore tests.

Excluded:

- reading or changing `wepp3`, its database, containers, volumes, services,
  firewall, credentials, backup locations, or production scheduler;
- changing or provisioning production-side access to the accepted backup host;
- declaring a production RTO achieved from development-sized data;
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
  destination on 2026-07-16. Production remains unauthorized.

## Assumptions and decisions

- Provider contract: encrypted `restic` storage at
  `forest1:/wc1/utility-watershed-analytics-db-backups`. This is off-host from
  production `wepp3`; development rehearsals on `forest1` use the same path
  locally and do not claim off-host evidence. The operator accepts that no
  independent object lock or storage administrator has been established.
- Encryption: `restic` repository encryption. The repository password and
  object-store credentials are separate root-readable credentials and never
  appear in repository files, command lines, logs, or evidence.
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
- production Compose is render-only and no production command is run.

Skipped gate and reason:

- production backup/restore and scheduler evidence: production access and
  mutation are not authorized;
- production backup-host transport: `forest1` is accepted, but production-side
  SSH/SFTP access and scheduling were not authorized or exercised;
- production RTO proof: a development-sized restore cannot establish it.

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

## Risks and recovery

- Risk: backup artifacts or logs expose credentials or role verifiers.
  - Prevention: mode-`0600` staging, root-readable credentials, redacted logs,
    secret scanning, encrypted transport, and no artifacts in Git.
  - Recovery or rollback: revoke exposed credentials, quarantine the artifact,
    rotate database and object-store access, and rerun from a clean target.
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
| Production transport, source, and reboot gates | `wepp3` and host reboot | Static | Not run; production access remains unauthorized and no host reboot was performed. |

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

### Terminal disposition

- Final status: `EXECUTED-HOLD-PRODUCTION-DRILL`
- Exit criteria disposition: repository implementation, isolated encrypted
  workflow, exact restore comparison, application smoke framework, failure
  injection, retention, recovery access, accepted provider/owner/RPO/RTO/alert
  decisions, and live `forest1` scheduler gates met; encrypted transport from
  `wepp3`, reboot persistence, and non-empty production-shaped evidence remain
  unmet.
- Blocker, if held: production access remains unauthorized, so the repository
  has not received or restored a representative `wepp3` backup.
- First follow-on action, if held: authorize a bounded encrypted
  `wepp3`-to-`forest1` backup and isolated restore drill without changing the
  serving production stack.
- Successor package, if any: DB02 repository work may proceed independently;
  DB03 and DB05 remain blocked on DB01 completion.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
