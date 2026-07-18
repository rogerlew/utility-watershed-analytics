# Database deployment serialization contract

Status: accepted DB25 repository contract

Date: 2026-07-18

DB25 defines the code/schema/data compatibility and least-privilege boundary
used by later deployment automation. It does not install roles or credentials
on `wepp3`, run production migrations, or implement DB26's orchestrator.

## Two-layer serialization

Every workflow containing a production-environment job uses the literal GitHub
concurrency group `utility-watershed-analytics-production` with
`cancel-in-progress: false`. `scripts/validate_deployment_serialization.py`
fails if a production workflow diverges. DB26 and DB27 must use that same group
when their workflows are added.

On the host, code deployment, schema migration, database role configuration,
credential rotation, data activation, restore, and other mutations require the
exclusive DB03 lock at
`/run/lock/utility-watershed-analytics/operations.lock`.
`scripts/require_operation_lock.sh` reasserts that the inherited descriptor is
open, names the canonical file, and has the required mode. A closed, stale,
wrong-file, or shared descriptor cannot cross an exclusive mutation boundary.
The GitHub group coordinates conforming workflows; the host lock also
coordinates systemd, operator, backup, and recovery processes.

## Explicit migration and startup

Production application deployment performs this order under one exclusive host
lock:

1. validate the minimized runtime and migration credential files;
2. preserve and dry-run-check the exact database identity;
3. build the new application image;
4. reassert the host lock;
5. run `python manage.py migrate --noinput` once with
   `uwa_migration_login` from the separate migration credential file;
6. run `check_application_compatibility` with the runtime identity;
7. build the frontend, reassert the lock, and replace application workers; and
8. verify unchanged database identity and application health.

The production entrypoint runs `python manage.py migrate --check --noinput`.
It never applies a migration. Therefore an ordinary restart cannot race or
substitute for the explicit migration step. The protected workflow writes the
runtime and migration files separately with mode `0600` and removes both in its
always-run cleanup.

## Executable compatibility

`check_application_compatibility` rejects pending or ambiguous migrations,
incoherent active-pointer state, unsupported contracts, and active releases
whose migration is unknown or older than the application's accepted minimum.
An `EMPTY` singleton remains a supported pre-adoption application state.

`check_release_compatibility` is the later orchestrator's read-only
pre-activation gate. It requires:

- the exact target release and live staged/applying attempt;
- the attempt's deployed application Git commit;
- supported schema, data, identity, artifact, and fingerprint contracts;
- the exact applied target migration;
- exact target and materializer image/Git plan coordinates;
- canonical reviewed/actual plan digest binding;
- the exact active base and operator-supplied base manifest, or coherent
  `EMPTY` state;
- validated target run states and exactly the seven required core artifact
  roles/media types for every run;
- `READY`, exact-count, completely validated staging; and
- semantically valid staged capability configuration.

The command locks the attempt, staging state, and active pointer while checking
but performs no activation. DB23 still rechecks the plan/base/fingerprints and
takes its transaction advisory lock inside the activation transaction.

## Database identities

`scripts/database_roles.sql` separates fixed NOLOGIN privilege roles from
rotatable LOGIN credential principals:

| Privilege role / login | Allowed boundary | Explicit denial boundary |
| --- | --- | --- |
| `uwa_status` / `uwa_status_login` | Read watershed domain, ledger, attempts, and staging for planning/status | No table writes, non-watershed reads, or privileged role assumption |
| `uwa_staging` / `uwa_staging_login` | Read watershed state; insert immutable target ledger/identity rows; write attempts and staging | No serving watershed, capability, alias, or active-pointer writes |
| `uwa_activation` / `uwa_activation_login` | DML on watershed tables and sequences for the reconciler transaction | No schema creation, migration, backup, or role administration |
| `uwa_runtime` / `uwa_runtime_login` | Read active serving, identity, release, artifact, and capability tables | No staging reads or any watershed write |
| `uwa_backup` / `uwa_backup_login` | PostgreSQL `pg_read_all_data` for complete logical backup | No writes, DDL, or role administration |
| `uwa_migration` / `uwa_migration_login` | Own the application schema/tables and run explicit Django DDL | No superuser, role administration, replication, or row-security bypass |
| `uwa_restore` / `uwa_restore_login` | Deliberate `SET ROLE uwa_restore` for restore/break-glass, with migration/activation/backup membership and create-role/database ability | Login is `NOINHERIT`; no ordinary access before explicit elevation |

All ordinary roles are non-superuser, cannot create databases/roles, cannot
replicate, and cannot bypass row security. Public schema creation is revoked.
The restore login forces PostgreSQL `log_statement=all` and `log_duration=on`,
so emergency elevation and statements are present in the database log. DB27
adds the operator approval/report binding around that audit stream.

Run role convergence after every explicit schema migration so grants cover the
new exact watershed tables. Role convergence changes ownership and grants and
therefore requires the exclusive lock, a privileged database administrator,
and separate production authority.

## Credential delivery and rotation

Role provisioning creates no password. `scripts/rotate_database_credential.sh`
accepts only one of the seven fixed LOGIN principals and reads the replacement
from a regular owner-matched mode-`0600` file. The password is sent to `psql`
over standard input, is not placed in an argument, and is never printed.

Runtime, migration, status, staging, activation, backup, and restore credential
files are delivered separately and can rotate independently. A rotation is
complete only after the new credential authenticates, the previous credential
fails, the expected permission probes pass, and the protected old secret is
removed. Production provisioning and first rotation belong to DB27A or another
explicitly authorized production package.

## Durable data deployment

DB26 implements the host-side consumer of this contract in
`scripts/deploy_database.sh`. It holds the same exclusive descriptor for the
whole attempt, reasserts it at backup/publication/activation/rollback
boundaries, persists private atomic phase state, and resumes only with the
same request and input hashes. The accepted phase order and systemd semantics
are documented in the
[database deployment orchestrator runbook](runbooks/database-deployment-orchestrator.md).

The active no-op path performs exact serving verification but invokes neither
backup nor activation. A changing release cannot activate until the DB25
compatibility phase and verified encrypted publication on
`forest1:/wc1/utility-watershed-analytics-db-backups` have passed. Post-pointer
smoke/refresh failure invokes only the reviewed DB22 inverse. DB26 provides no
production authority, phase-package installation, or protected workflow;
those remain explicit later operations.
