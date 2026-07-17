# System Administration Agent Guide

## Scope and ownership

These instructions apply to system-administration plans, runbooks, and task
records under `docs/sys-administration/`.

Agents have authoring ownership of these records. Keep the instructions,
execution log, evidence summary, and closeout state coherent as an
administrative task progresses. This ownership does not grant access to a host
or permission to run a command. Production authority must be explicit for the
specific task and must identify the permitted hosts and mutation boundary.

Keep the process proportionate to this small, single-operator, public-data
service. Use a short task record and clear checkpoints rather than adding
approval ceremony that does not improve safety or recovery.

## Host boundaries

- `forest1` is the development server and accepted encrypted backup host. Use
  it for repository work, backup storage under
  `/wc1/utility-watershed-analytics-db-backups`, and isolated restore targets.
- `wepp3` is production. Do not inspect it, copy data from it, change it, or
  restart its services without explicit task-specific authority.
- Read-only production access, creation of a production backup, service or
  configuration mutation, and restoration into a serving database are
  separate authorities. Permission for one does not imply another.
- A `wepp3` to `forest1` drill must leave the serving production stack and
  database unchanged. Restore only into a disposable, isolated target on
  `forest1` unless serving-database restore authority is separately stated.

## Task record

Create one local Markdown record per administrative task in
`docs/sys-administration/logs/` named `YYYYMMDD-HHMM-<short-slug>.md`, using the
operator's local time. The task logs are intentionally Git-ignored. Start the
record before the first remote command and update it as work occurs; do not
reconstruct a successful-looking log later.

Record the minimum facts needed to review and recover the operation:

- objective, operator, date, starting repository commit, and task status;
- the user's authority in plain language, including source host, target host,
  allowed reads and mutations, and explicit exclusions;
- exact source and target identities, expected artifacts, preflight checks,
  rollback or cleanup, and stop conditions;
- each material command with timestamp, host, redacted command, exit status,
  and a concise result;
- artifact identifiers, checksums, sizes, permissions, and filesystem paths
  without embedding the artifact itself;
- verification results, deviations, failures, cleanup, and the final status;
  and
- evidence classification as **Ran**, **Static**, or **Mixed**, consistent
  with `docs/work-packages/README.md`.

Use status values `PLANNED`, `RUNNING`, `COMPLETE`, `HOLD`, or `ABORTED`. A
`HOLD` or `ABORTED` record must state the blocker, observed system state,
cleanup performed, and safest next action.

## Execution discipline

- Begin with non-mutating preflight: confirm hostnames, current time, disk
  capacity, tool versions, source and target identities, repository state, and
  required credentials without printing secret values.
- State the next material action before running it. Use bounded, reviewable
  commands and inspect their results before continuing.
- Stop on an unexpected host, container, volume, database, image, snapshot,
  path, checksum, permission, capacity result, or non-zero exit. Record the
  discrepancy before deciding whether a newly authorized retry is safe.
- Use least privilege. Do not use `docker compose down`, prune Docker or backup
  data, initialize a replacement backup repository, alter production services,
  or restore over a serving database unless the task explicitly authorizes that
  exact action.
- Preserve unrelated workloads and files on both hosts. Clean up only
  disposable resources created by the task and confirm that cleanup in the
  record.
- Follow the authoritative repository runbook for the operation. For database
  backup and restore work, use `docs/runbooks/database-backup-restore.md` and
  the active DB01 work package rather than inventing an alternate procedure.

## Logging and secret handling

- Capture enough output to prove the result, but prefer concise summaries and
  identifiers over full command transcripts.
- Never log or commit passwords, tokens, private keys, full environment files,
  connection URLs containing credentials, database globals, credential
  verifiers, raw database dumps, restic repository contents, or production row
  data.
- Avoid placing secrets in command arguments or shell history. Use protected
  files, environment indirection, and existing credential mechanisms.
- Redact before writing to the local task record or any repository evidence
  record. Do not write a secret first and remove it later; terminal capture and
  copied evidence may retain it.
- Keep bulky or sensitive evidence outside Git with operator-only permissions.
  The local record may contain its safe path, checksum, size, retention
  expectation, and verification result. Copy only a sanitized durable summary
  into an active work package when repository evidence is required.
- Preserve failure evidence honestly. A successful archive command is not a
  restore test, an isolated `forest1` result is not production evidence, and a
  retry does not erase the first failure.

## Closeout

Before marking a task `COMPLETE`:

1. verify the intended outcome from an independent read where practical;
2. confirm production service health and that excluded state was unchanged;
3. confirm backup or restore artifacts have the expected encryption,
   permissions, identity, checksum, and retention disposition;
4. remove disposable task resources and record anything intentionally retained;
5. scan the local record for secrets and prohibited artifacts, and run
   `git diff --check` if the task changed repository files; and
6. reconcile any affected runbook, work package, roadmap status, or durable
   operational fact without overstating the evidence.

Repository commits and pushes require their own explicit authority. Do not
open a pull request or perform additional administrative work merely because a
task record is complete.
