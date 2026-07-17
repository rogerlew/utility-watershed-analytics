# Database Backup and Restore Runbook

Status: repository contract; production installation pending DB01 acceptance

This runbook implements the backup and restore controls required by DB01. It
does not authorize production access or mutation. `forest1` is the shared
development server. `wepp3` is production, and every production read, install,
backup, restore, maintenance action, or service change requires the authority
recorded by the active work package.

## Recovery objectives and owners

- Maximum RPO: 24 hours. The daily timer and six-hour freshness monitor allow
  one additional hour for scheduler jitter and notification response before
  reporting the newest encrypted snapshot stale.
- Maximum RTO: 24 hours. A development restore duration is evidence about
  tooling, not production-scale capacity.
- Credential and recovery owner: this is a single-operator service. The project
  operator, currently the `roger` account owner, controls the restic password,
  backup-host access, recovery, restore approval, and restore execution.
- Restore authority: the project operator grants operation-specific authority
  after reviewing the exact source snapshot, target, maintenance plan,
  rollback, and expected data loss.

These single-operator choices may be revisited if another maintainer joins or
the service becomes materially more sensitive or operationally critical.

## Backup format

`scripts/backup_database.sh` creates one mode-`0700` atomic local staging set:

- `database.dump`: custom-format database archive;
- `globals.sql`: roles, memberships, grants, password verifiers, and
  tablespaces; treat it as a credential-bearing secret;
- `schema.sql` and `archive.toc.txt`;
- `inventory/`: secret-free roles, memberships, extensions, migrations,
  sequences, table counts, and constant-memory logical fingerprints;
- `metadata.txt`, `checksums.sha256`, and `complete`; and
- `backup.log`.

The script fully decodes the archive before publishing `complete`. It never
deletes an earlier set. A completion marker proves only local archive creation;
it does not prove encryption, off-host durability, or restorability.

`scripts/publish_backup.sh` rechecks the set, publishes it into the encrypted
restic repository, and runs `restic check` with a rotating data subset. Restic
snapshot identity is the accepted off-host backup identity. Provider-side
versioning or object lock is required so a compromised writer cannot silently
erase the only recovery copy.

## Provider acceptance

The accepted backup host is `forest1`, with repository storage rooted at
`/wc1/utility-watershed-analytics-db-backups`. From production `wepp3`, use an
encrypted restic SFTP repository such as
`sftp:forest1:/wc1/utility-watershed-analytics-db-backups/repository`. A local
development rehearsal on `forest1` uses the filesystem path directly and is
same-host evidence only.

The project operator accepts this simple arrangement because the application
data is public and has no end-user accounts or PII. Restic encryption remains
required because database-global backups can contain credential verifiers.
Directory permissions must remain operator-only. No independent storage
administrator, immutable object lock, or external alert channel is required at
this stage; those are explicit residual risks rather than unimplemented hidden
requirements.

Before production scheduling, exercise repository upload, list, download, and
password recovery from `wepp3`, then restore into an isolated disposable target.
Preserve a sanitized acceptance report; never preserve credentials or the
restic password in Git.

### Current `forest1` operator profile

The accepted repository is initialized and the development rehearsal is active:

- encrypted repository: `/wc1/utility-watershed-analytics-db-backups/repository`;
- protected runtime configuration:
  `~/.config/utility-watershed-analytics/backup.env`;
- protected restic password:
  `~/.config/utility-watershed-analytics/restic-password`;
- local restic client: `~/.local/bin/restic`;
- daily user timer: `uwa-db-backup.timer`;
- weekly retention timer: `uwa-db-retention.timer`; and
- weekly restore-test timer: `uwa-db-restore-test.timer`.

The `roger` user has lingering enabled so these user timers continue after
logout. Inspect them without special tooling:

```bash
systemctl --user list-timers 'uwa-db-*' --all
systemctl --user --failed
journalctl --user -u uwa-db-backup.service -n 50
```

These timers currently back up the development `postgis` container on
`forest1`. They prove the destination and schedule but do not replace the later
authorized `wepp3` schedule.

Initialize exactly once after confirming the intended repository string:

```bash
sudo --preserve-env=RESTIC_REPOSITORY,RESTIC_PASSWORD_FILE \
  restic snapshots
# Only "repository does not exist" is an acceptable initialization condition.
sudo --preserve-env=RESTIC_REPOSITORY,RESTIC_PASSWORD_FILE \
  restic init
```

Do not automate `restic init` in the daily job. A mistyped bucket must fail
rather than create a second repository that appears healthy.

## Credentials and installation

Install a reviewed restic release and record its version and package source.
Create the configuration directory and files without shell history or process
arguments containing secret values:

```bash
sudo install -d -o root -g root -m 0700 \
  /etc/utility-watershed-analytics
sudo install -o root -g root -m 0600 \
  ops/backup/backup.env.example \
  /etc/utility-watershed-analytics/backup.env
sudo install -o root -g root -m 0600 /dev/null \
  /etc/utility-watershed-analytics/restic-password
sudo install -o root -g root -m 0600 /dev/null \
  /etc/utility-watershed-analytics/backup-failure-webhook
```

Populate the installed files through the approved secret-delivery mechanism.
`backup.env` contains only backup-specific values. It must not reuse or copy the
application's complete production environment file. The webhook file contains
one HTTPS URL. The restic password file contains the repository password only.

Install and verify units only in an authorized package:

```bash
sudo install -o root -g root -m 0644 ops/systemd/*.service \
  ops/systemd/*.timer /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/utility-watershed-analytics-*.service \
  /etc/systemd/system/utility-watershed-analytics-*.timer
sudo systemctl daemon-reload
sudo systemctl enable --now utility-watershed-analytics-backup.timer
sudo systemctl enable --now utility-watershed-analytics-backup-freshness.timer
sudo systemctl enable --now utility-watershed-analytics-backup-retention.timer
sudo systemctl enable --now utility-watershed-analytics-restore-test.timer
```

The timers use `Persistent=true`; a missed run is started after the host returns.
Verify that behavior through an authorized reboot drill and record the timer's
pre-reboot next-elapse, post-reboot last-trigger, service result, off-host
snapshot ID, and notification behavior.

## Routine operation

Inspect without changing the stack:

```bash
systemctl list-timers 'utility-watershed-analytics-*'
systemctl status utility-watershed-analytics-backup.service
journalctl -u utility-watershed-analytics-backup.service --since today
sudo -E scripts/check_backup_freshness.sh
```

A successful run must have all of the following:

1. a completed local backup set;
2. a restic snapshot tagged `uwa-database` and `scheduled`;
3. a passing repository check;
4. a current `last-success` state record;
5. a freshness check younger than `BACKUP_MAX_AGE_SECONDS`; and
6. no failure-notification event.

The local staging set is sensitive and is not the durable copy. Retain only the
short operational window approved for retry and diagnosis, on encrypted host
storage. Never move it into the repository. Automate local cleanup only after
the off-host snapshot and restore-test history are verified.

## Failure and stale-backup response

Every backup, freshness, retention, and restore-test unit invokes
`utility-watershed-analytics-backup-failure@.service` through `OnFailure`.
`scripts/notify_backup_failure.sh` writes to the system journal and can post to
a configured HTTPS webhook. DB01 initially accepts the systemd journal and
failed-unit state as the single operator's alert channel; adding an external
webhook later does not require redesigning the backup flow.

On alert:

1. acknowledge through the accepted incident channel;
2. preserve unit status and sanitized logs;
3. distinguish source database, local staging, network, credentials, provider,
   retention, and restore-test failures;
4. do not initialize a new repository or prune anything during diagnosis;
5. run a bounded retry only after correcting the identified fault;
6. verify the new snapshot from a separate reader context; and
7. record recovery-point age and whether the 24-hour RPO was exceeded.

Exercise a forced failure with an isolated configuration by setting
`BACKUP_FORCE_FAILURE=after-local-backup`. Confirm non-zero service status,
local log entry, external notification, sensitive staging containment, and a
successful later retry. Never inject this failure into an unreviewed production
schedule.

## Retention

Scheduled snapshot defaults are 14 daily and 8 weekly. Release-point snapshots
are also tagged `release-point` and `release:<exact-id>`, so time retention does
not remove them.

Before applying release retention, obtain the exact active release and two
rollback release IDs from authoritative release state. Preview first:

```bash
scripts/backup_retention.py \
  --retain-release ACTIVE \
  --retain-release ROLLBACK_1 \
  --retain-release ROLLBACK_2
```

Apply and prune only after the report identifies the intended obsolete snapshot
IDs:

```bash
scripts/backup_retention.py \
  --retain-release ACTIVE \
  --retain-release ROLLBACK_1 \
  --retain-release ROLLBACK_2 \
  --apply --prune
```

The command rejects duplicate or fewer-than-three retained release IDs, refuses
unknown retained releases, preserves the newest snapshot for each exact
retained ID, and removes older or unlisted release-point snapshots. Provider
versioning/object lock is the recovery control for an operator or tooling
mistake. Test that recovery before enabling automated pruning.

## Isolated restore test

`scripts/run_restore_test.sh` performs the scheduled drill:

1. selects the globally newest `uwa-database` snapshot;
2. restores its encrypted contents to mode-`0700` disposable staging;
3. starts the exact recorded PostGIS image with no published ports on an
   internal temporary network;
4. waits through the PostGIS image's initialization restart;
5. verifies checksums and restores globals and the database;
6. compares source roles, memberships, extensions, migrations, sequences,
   schema, and every table count/fingerprint;
7. runs `python manage.py restore_smoke` from the pinned server image for
   database connectivity, system checks, watershed list, and representative
   detail, subcatchment, and channel reads; and
8. fails when total retrieval, restore, comparison, and application time exceeds
   `BACKUP_MAX_RTO_SECONDS`.

The test accepts no target container argument and creates its own container with
the required disposable-target label. `scripts/restore_database.sh` independently
rejects an unlabeled target, the recorded source container, an existing target
database, checksum drift, incompatible versions, or comparison drift.

`RESTORE_ALLOW_EMPTY_DATABASE=true` exists only for early development fixtures.
Production restore tests must leave it false and require representative API
reads from restored watershed data.

## Maintenance and full disaster restore

Full restore rolls back all database state, including authentication, admin,
sessions, and other non-watershed writes after the selected snapshot. Use it
only with operation-specific authority.

### Enter maintenance

1. Acquire the canonical host-wide exclusive operations lock defined by DB02.
2. Record approver, operator, incident, source snapshot ID and age, target
   container/image/volume IDs, expected data-loss interval, and rollback.
3. Enable the reviewed Caddy maintenance response before stopping application
   writers; do not use `docker compose down`.
4. Stop or isolate server and worker writes while leaving PostgreSQL running.
5. Prove quiescence through application state, active sessions, and a bounded
   write-observation interval.
6. Preserve the target volume through a stable exact reference and take any
   final readable backup required by the incident plan.

### Restore

1. Verify offline recovery credentials from the recovery owner.
2. Retrieve the exact selected restic snapshot into protected staging.
3. Verify `complete` and `checksums.sha256` before reading `globals.sql`.
4. Provision the exact compatible PostGIS image and an empty named target
   volume. Never mount an empty volume into the serving Compose project first.
5. Restore globals as a temporary cluster superuser, then restore
   `database.dump` with `pg_restore --create --exit-on-error`.
6. Compare the recorded inventories and schema exactly. Investigate every
   difference; do not waive failed role, extension, migration, sequence, count,
   or fingerprint checks.
7. Run the pinned server image's `restore_smoke` command without
   `--allow-empty`, followed by the externally routed health and representative
   API checks required by the incident plan.
8. Record achieved RPO and RTO, versions, snapshot and image IDs, checksums,
   counts, fingerprints, and results.

### Exit maintenance

1. Point only the reviewed runtime configuration at the accepted restored
   volume; inspect the proposed Compose action and reject database recreation.
2. Start application services without invoking legacy `down` behavior.
3. Re-run database, internal API, public API, authentication, and admin smoke
   checks.
4. Remove maintenance mode only after the incident commander accepts results.
5. Keep the former target and restored staging through the rollback window;
   prevent ordinary volume prune.
6. Complete and restore-test a new encrypted off-host scheduled backup.

## Selective restore

Never replay selected custom-archive tables directly into production. Foreign
keys, sequences, application writes, and related rows can make that unsafe.

1. Obtain separate read and mutation authority and acquire the exclusive lock.
2. Restore the complete snapshot into an isolated labeled target.
3. Identify exact rows and dependencies with reviewed read-only queries.
4. Export only the accepted rows into protected staging with explicit columns,
   stable keys, counts, and checksums; exclude credentials unless credential
   recovery is the authorized purpose.
5. Prepare a transaction-scoped apply and inverse plan against a
   production-shaped rehearsal.
6. Take and verify a fresh encrypted off-host backup of current production.
7. Enter maintenance or otherwise prove the required write quiescence.
8. Apply the exact reviewed set in one transaction, reset affected sequences,
   verify counts/fingerprints and APIs, and record the audit trail.
9. Roll back the transaction or apply the reviewed inverse on failure. Escalate
   to full restore only through the separately reviewed disaster procedure.

## Roles and operational accounts

`globals.sql` recreates cluster roles, memberships, grants, password verifiers,
and tablespaces. Restore it only into an isolated or empty compatible cluster;
never pipe it blindly into a serving cluster. The secret-free `roles.tsv` and
`role-memberships.tsv` inventories prove expected source entries after restore.
The temporary bootstrap superuser may remain as an extra role during an
isolated drill but must be removed or rotated according to the accepted
production recovery plan.

A full database restore already includes application accounts present at the
snapshot. A disaster rebuild from migrations and release artifacts does not.
For that path, seed only explicitly required operational accounts from the
protected recovery configuration:

```bash
DJANGO_SUPERUSER_USERNAME=... \
DJANGO_SUPERUSER_EMAIL=... \
DJANGO_SUPERUSER_PASSWORD=... \
python manage.py createsuperuser --noinput
```

Deliver values through the approved secret mechanism, not shell history or a
committed environment file. Immediately rotate temporary recovery passwords
and verify MFA or institutional access controls where applicable.

## Encryption-key recovery

At least quarterly and before relying on a new repository format:

1. use the recovery owner's copy on a host without the online writer secret;
2. obtain read-only break-glass object-store credentials;
3. run `restic snapshots`, restore a selected set, verify checksums, and execute
   the isolated database/application drill;
4. record only credential identifiers, versions, approvers, snapshot ID,
   timings, and results; and
5. rotate any credential exposed beyond its intended ceremony.

Loss of the restic password makes snapshots unrecoverable. A copy stored only
on `wepp3`, only in the same object-store account, or only with one individual
does not satisfy recovery ownership.
