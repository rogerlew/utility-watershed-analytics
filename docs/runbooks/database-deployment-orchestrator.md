# Database Deployment Orchestrator

Status: accepted DB26 repository contract; not installed on production

`scripts/deploy_database.sh` is the only host entry point for a reviewed data
release. It acquires DB03's exclusive lock and runs a private, atomic,
resumable state machine through the fixed phase adapter. `forest1` is the
development/rehearsal host. `wepp3` is production; this runbook and the unit do
not authorize access, installation, start, activation, rollback, or secrets on
`wepp3`.

## Simple operating model

1. DB27 prepares one reviewed request and four immutable input files.
2. The operator places the request, its separately reviewed SHA-256, and the
   minimized mode-`0600` secret file on the authorized host.
3. The operator explicitly starts one instance of
   `utility-watershed-analytics-database-deploy@.service`.
4. Systemd owns the process. Closing SSH has no effect. Do not use tmux.
5. Read `state.json`, `report.json`, and the journal for status. A stopped,
   killed, or rebooted nonterminal operation resumes only after an explicit
   start with the same immutable coordinates.

The unit is root-owned, `Type=oneshot`, `Restart=no`, has an eight-hour start
timeout and two-minute stop timeout, and is not installable as a boot target.
`KillMode=mixed` terminates the runner and its current phase together. TERM,
HUP, and INT leave resumable private state; SIGKILL leaves the last atomic
phase boundary. Every resume runs recovery before continuing.

## Reviewed request

Start from `ops/database-deployment/request.json.example`. The request itself
and every referenced input must be an ordinary owner-matched read-only file.
The supplied request SHA-256, all four input SHA-256 values, target release,
expected base manifest, application/materializer Git commits, digest-pinned
tool image, and local image ID are immutable resume coordinates. Any drift
fails before a phase runs.

The four inputs are the DB08 release document, the exact materialization member
index, and DB22's forward and bound inverse plans. DB26 does not reinterpret or
write watershed data. Root-owned phase programs call the existing DB16 and
DB20–DB25 recovery, staging, compatibility, reconciliation, validation, and
rollback interfaces. The fixed adapter accepts only these phase names:

```text
recover preflight classify prepare stage compatibility backup publish apply
smoke refresh report rollback rollback_smoke archive cleanup alert
```

Each program receives the request, durable state, operation directory, and
secret-file path, and returns one bounded JSON object with
`{"status":"passed"}`. Programs are installed below
`/usr/local/lib/utility-watershed-analytics/database-deployment-phases`, owned
by root, and not group/world writable. A different adapter or phase root is
accepted only with `UWA_DB_DEPLOY_TEST_MODE=1`; never set that variable in an
installed environment. The reviewed phase program bundle and DB27 approval
binding may not change this state-machine order or replace the DB16/DB20–DB25
mutation APIs with a second writer.

## Fail-closed order

- Recovery and preflight happen before classification.
- An exact active no-op runs serving smoke and reports, but never invokes
  backup, publish, apply, rollback, or worker refresh.
- A change stages and passes DB25 compatibility before backup.
- Activation requires a completed local backup SHA-256 and a verified restic
  publication receipt in the accepted encrypted repository on
  `forest1:/wc1/utility-watershed-analytics-db-backups`.
- Backup failure, stale base, wrong digest, lock loss, or any pre-activation
  failure never invokes rollback or activation.
- After activation, smoke must pass and `refresh` must invalidate discovery
  state or restart affected workers. A smoke/refresh failure invokes only the
  reviewed exact inverse, then rollback smoke and a second refresh.
- Rollback failure is terminal and distinct. There is no automatic retry.

The exclusive host descriptor is rechecked before backup, publication,
activation, and rollback. Phase programs must be idempotent at their durable
boundary because process loss can occur after a phase's external effect but
before its result is recorded.

## State, reports, and alerts

The default state root is
`/var/lib/utility-watershed-analytics/database-deployments`. Operation
directories are mode `0700`; state, results, report, and log files are atomic
mode `0600`. Adapter JSON rejects credential-shaped keys/values. Stderr and
failure summaries are bounded and redacted. Never write environment contents,
database URLs, tokens, passwords, raw plans, or row-level data to a result.

The `archive` phase copies the sanitized terminal report over the accepted
restricted transport to
`forest1:/wc1/utility-watershed-analytics-db-deployment-reports`. The cleanup
phase enforces the configured terminal-report retention (default 180 days) but
must never remove nonterminal state. `alert` emits sanitized journal status for
failed, resumed/stale, rolled-back, or rollback-failed operations. The current
single-operator service accepts journal alerts; DB27 may add notification
delivery without placing a webhook or token in repository files.

Inspect an authorized installation with:

```bash
systemctl status utility-watershed-analytics-database-deploy@OPERATION.service
journalctl -u utility-watershed-analytics-database-deploy@OPERATION.service
sudo cat /var/lib/utility-watershed-analytics/database-deployments/OPERATION/state.json
```

Do not delete or edit nonterminal state. To abandon an attempt, first recover
the database lease/staging state under separate explicit authority, preserve
the report, and record the reason.
