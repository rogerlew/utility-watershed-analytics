# DB26 — Production database deployment orchestrator

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB26`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic immutable inputs,
fake secrets, disposable phase adapters, disposable PostGIS/containers,
process interruption, durable-unit simulation, reboot-boundary simulation, and
forest1-local report/backup fixtures. It excludes `wepp3`, production secrets,
real releases/plans/backups, production activation/rollback, system-unit
installation or start, workflow dispatch, commit, push, PR, and external
mutation.

## Objective

Provide one durable, non-interactive, fail-closed host orchestrator that holds
the DB03 lock across recovery, verified inputs, preparation/staging,
off-host-backup proof, activation, smoke, report, optional exact rollback, and
cleanup without duplicating the DB20–DB25 data rules.

## Decisions

- Implement a host state machine whose only mutation interface is a fixed
  root-owned phase-program adapter; synthetic acceptance swaps in a bounded
  fixture adapter only under explicit test mode.
- Persist atomic mode-0600 state and reports after every phase under a
  mode-0700 operation directory. Resume validates immutable coordinates and
  recovers nonterminal database attempts before continuing.
- Require the canonical exclusive host lock for the entire process and recheck
  it before backup, activation, and rollback.
- Verify the digest-pinned tool image and exact read-only release/forward/
  inverse inputs before phase execution.
- Treat a verified active no-op as terminal before backup. Otherwise require a
  locally completed backup plus verified forest1 off-host publication receipt
  before activation.
- On post-activation smoke failure, run only the supplied exact inverse through
  the rollback phase. A pre-activation failure never invokes rollback.
- Use a root-owned oneshot unit with no automatic restart. Signals leave
  durable resumable state; the client session is irrelevant after systemd
  starts the unit.

## Gates

- `git diff --check`, shell syntax, ShellCheck when available, unit/static
  validation, and exact release-tool/server image regressions.
- Success, verified no-op, failed backup, stale base, failed smoke plus exact
  rollback, explicit rollback failure, interruption, process crash, lost
  client session, and simulated reboot/resume.
- Wrong input hash, writable/symlink input, wrong tool digest, lock loss,
  coordinate drift on resume, and incomplete recovery fail closed.
- No-op creates no backup and invokes no activation phase.
- Reports/logs/state are private, sanitized, atomic, durable after failure, and
  copied to the configured forest1 report archive with bounded retention.
- Durable unit uses an explicit principal, oneshot/no-restart semantics,
  bounded start/stop timeouts, and signal-safe behavior.
- Successful activation invokes the bounded worker refresh hook; rollback does
  so again after restoring the prior release.
- Documentation, scope, secrets, links, and disposable cleanup.

## Execution record

- Added an exclusive-locking shell entry point and Python state machine with
  exact request/input/tool coordinates, atomic private state, bounded sanitized
  logs/results, explicit resume, and phase-boundary lock rechecks.
- Added the root oneshot instance unit with no restart or boot target, bounded
  timeouts, mixed kill semantics, journal output, and explicit request/hash
  inputs. The unit was verified but not installed or started.
- Proved success and exact active no-op. The no-op call trace contained smoke,
  report, archive, and cleanup but no backup, publish, apply, rollback, or
  refresh.
- Proved failed backup and stale-base compatibility stop before activation;
  failed post-activation smoke ran exact rollback, rollback smoke, and refresh;
  an injected rollback failure remained distinct and terminal.
- Proved TERM interruption, SIGKILL process loss, simulated reboot loss, and a
  detached/lost client session. Every nonterminal restart ran recovery first,
  retained immutable coordinates, and completed without SSH/tmux ownership.
- Proved mode-0600 state/report/log/results, secret-shaped adapter-result
  rejection, terminal-state retention, and forest1-local archive fixtures.
- Revalidated the exact release-tool image and exact DB25 production server
  image checks. No data source, real release, real backup, `wepp3`, production
  secret, service, workflow, commit, push, or external system was touched.

### Commands and evidence

| Gate | Result |
| --- | --- |
| State-machine acceptance | Passed 3 end-to-end tests covering the fixed adapter boundary, success, no-op, backup failure, stale base, smoke rollback, rollback failure, report-archive failure, interruption, process crash, reboot boundary, lost client, recovery-first resume, archive, and retention |
| Exact release-tool image | Passed audited image `sha256:14fd35b2cbfeac308cd796e466af1acf59c29f5e70ddea72cfa950a057217b42` |
| Exact server image | DB25 production image `sha256:2e355618f60d3d7b4107a52de1599ce49f26fb38cad2819601d9213b5b46efcf` passed Django deploy checks at error threshold; 14 established warnings remained warnings |
| Unit and shell | Bash/Python syntax, `systemd-analyze verify`, and `git diff --check` passed; ShellCheck was unavailable |
| Production boundary | No `wepp3`, production data/secret/service/workflow, unit installation/start, activation, rollback, backup, or external mutation |

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met with Mixed evidence
- Blocker: none
- First follow-on action: scaffold DB27 protected release workflow, roles, and
  status without dispatching or installing production components
- Successor package: DB27, not yet scaffolded

## Artifacts

- `artifacts/db26-validation-evidence.md`
- `docs/runbooks/database-deployment-orchestrator.md`

## Closeout checklist

- [x] Package status/evidence mode are accurate.
- [x] Gates and skipped reasons are recorded.
- [x] Evidence contains no credentials, real coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match authority.
