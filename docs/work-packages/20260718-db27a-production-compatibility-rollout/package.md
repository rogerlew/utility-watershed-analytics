# DB27A — Production compatibility schema and code rollout

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB27A`

Evidence mode: Mixed

Execution authorization: On 2026-07-18 the operator explicitly requested
scaffolding and execution of DB27A after separately authorizing DB27 commit and
push. This authorizes Codex, acting as operator, to inspect and mutate the
bounded `wepp3` production schema/application path described here and to use
`forest1` for the fresh encrypted backup, isolated production-shaped rehearsal,
and sanitized evidence. `roger` is approver and rollback owner. The authority
does not include legacy-base adoption, watershed data activation, destructive
schema or data changes, PostgreSQL/PostGIS upgrade, unrelated host changes,
reboot, DB28 or later work, current-package commit/push, PR creation, or a data
release workflow dispatch.

## Objective

Under the canonical exclusive host lock and after a fresh verified encrypted
backup to `forest1:/wc1`, apply the additive DB13–DB16 compatibility migrations,
converge least-privilege database roles, and deploy dual-compatible application
code while retaining the current public data and `EMPTY` release-ledger
behavior.

## Scope

Included:

- freeze exact production repository, runtime, database, image, schema, role,
  data-count, public-identity, capability, API, lock, backup, and capacity state;
- create and independently verify a fresh encrypted production backup on
  `forest1`;
- restore that backup into an isolated production-shaped target on `forest1`,
  rehearse forward migration/code deployment, rollback to the pre-migration
  boundary, and roll forward again;
- provision or converge the DB25 production role and migration-credential
  boundary without exposing credentials;
- run the migrations exactly once under the shared exclusive lock and deploy
  the dual-compatible application code;
- verify unchanged watershed and non-watershed data, public identities, API
  behavior, observed legacy capabilities, runtime/database identity, and
  `EMPTY` release state;
- record migration duration, lock behavior, schema signatures, role results,
  rollback boundary, cleanup, and sanitized evidence.

Excluded:

- legacy-base capture, registration, adoption, release preparation, activation,
  rollback, or any real release artifact/plan;
- modifying or deleting existing watershed/non-watershed rows except additive
  migration backfills required by the reviewed schema;
- PostgreSQL/PostGIS image, volume, Compose project, database identity, backup
  repository, retention policy, or operating-system changes;
- reboot, destructive migration rollback on production, force push, PR, or
  unrelated GitHub settings/secrets/workflows.

## Frozen dispatch coordinates

- Repository: `/workdir/utility-watershed-analytics`
- Starting revision: `5b358c1` (`Complete DB27 protected release workflow`)
- Working branch: `agent/database-backup-deployment-spec`
- Push target for DB27: `origin/agent/database-backup-deployment-spec`, complete
- DB27A commit/push: not authorized in this package
- Pull request: do not open
- Development/rehearsal host: `forest1`
- Production host: `wepp3`
- Backup destination: encrypted repository rooted at
  `forest1:/wc1/utility-watershed-analytics-db-backups`
- Production checkout: `/workdir/utility-watershed-analytics`
- Production lock: `/run/lock/utility-watershed-analytics/operations.lock`
- Production Compose project: `utility-watershed-analytics`
- Production database volume: `utility-watershed-analytics_postgres_data`
- Executor: Codex; approver and rollback owner: `roger`

Production's exact starting commit, image IDs, database identity, schema
signature, role state, snapshot ID, and public fingerprints must be captured by
read-only preflight. Any mismatch with the durable runtime contract is a hold,
not permission to repair something unrelated.

## Plan

1. Freeze production coordinates and invariant baselines read-only.
2. Create and independently verify a fresh encrypted off-host backup.
3. Restore the backup into isolated `forest1` and rehearse forward, rollback,
   and forward compatibility boundaries.
4. Converge the reviewed migration/runtime role boundary without printing
   secrets.
5. Under the exclusive host lock, apply one-shot migrations and deploy the
   dual-compatible application.
6. Recheck schema, roles, data/API/capability invariants, runtime health, and
   backup visibility; remove only disposable task resources.

## Gates and stop conditions

- S0, DB19A, DB25, DB26, and DB27 remain complete at starting revision.
- Production checkout is clean and its exact deployment source is an ancestor
  of the reviewed target; no force, merge commit, or unrelated publication.
- Canonical runtime, named database volume, pinned database image, lock, backup
  timers/repository, disk/WAL margin, and public service are healthy.
- A task-fresh encrypted backup is independently visible on `forest1` before
  schema or application mutation.
- Isolated restore matches production inventories/fingerprints and passes the
  exact forward/rollback/forward rehearsal within the accepted recovery budget.
- Migrations are additive, one-shot, lock-bounded, and leave the ledger
  `EMPTY`; ordinary application startup remains migration-check-only.
- Production database/container/image/volume identity, watershed and
  non-watershed invariants, public identities, API behavior, and observed
  legacy capability behavior remain accepted after deployment.
- Least-privilege roles and credential files match the DB25 contract without
  secret material entering logs or Git.
- Stop on unexpected host, checkout, dirty worktree, service, image, volume,
  schema, role, data, public response, backup, capacity, lock, credential,
  migration, or workflow result. Do not improvise a repair across the boundary.

## Rollback boundary

Before production migration, rollback is no production change. After additive
migration but before worker replacement, retain the new schema and redeploy the
exact pre-DB27A application image/code, whose compatibility must be proved in
the isolated rehearsal. After worker replacement, the same code rollback
remains available while the additive schema stays in place. Destructive
production schema rollback is excluded; failure of the compatibility boundary
is `EXECUTED-HOLD-ROLLBACK` and requires a separate restore decision.

## Exit criteria

`EXECUTED-COMPLETE` requires a verified fresh backup, exact isolated
forward/rollback/forward rehearsal, one-shot production migration and
dual-compatible code deployment under the canonical lock, accepted roles and
schema signatures, unchanged production data/API/capability/runtime invariants,
clean disposable-resource removal, and honest sanitized evidence.

Legitimate terminal holds include `EXECUTED-HOLD-IDENTITY`,
`EXECUTED-HOLD-BACKUP`, `EXECUTED-HOLD-REHEARSAL`,
`EXECUTED-HOLD-CREDENTIALS`, `EXECUTED-HOLD-MIGRATION`,
`EXECUTED-HOLD-DEPLOY`, `EXECUTED-HOLD-ROLLBACK`, and
`EXECUTED-HOLD-VERIFICATION`.

## Execution record

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Authority and package scaffold | repository / `forest1` | Static | Starting revision, hosts, backup destination, mutation boundary, exclusions, operator, approver, rollback owner, gates, and stop conditions recorded before remote access. |
| Production read-only freeze | `wepp3` | Ran | Correct host; fork `main` checkout at `ae74c39...`; canonical unit/lock/named volume and pinned database image healthy; migration `0006`; 126 watersheds, 195,457 subcatchments, 86,895 channels, zero accounts/sessions; no DB25 roles; public schema and watershed routes returned 200. |
| Fresh encrypted backup | `wepp3` / `forest1` | Ran | Scheduled backup produced 1,217,146,341-byte verified archive SHA-256 `78c866c4...`; encrypted snapshot `08321397...` is independently visible on `forest1`; repository metadata and a 1/100 data subset check passed. |
| Exact isolated restore | `forest1` | Ran | Snapshot `08321397...` restored into exact-image disposable PostGIS in 351 seconds; roles subset, extensions, migrations, sequences, schema, and every table fingerprint matched. |
| Compatibility rehearsal | isolated `forest1` | Ran | Forward migrations completed in 35 seconds; exact pre-rollout image remained compatible and returned the same sorted 126-feature public payload; new startup was migration-check-only and new status reported `EMPTY`. |
| Rollback/roll-forward rehearsal | isolated `forest1` | Ran | Disposable schema rollback completed in 26 seconds and returned watershed fingerprints/migrations/extensions; Django metadata sequences and live legacy Silk telemetry advanced, confirming destructive production schema rollback is not exact and remains excluded. Second forward ran as `uwa_migration_login` in 32 seconds. |
| Least-privilege/runtime rehearsal | isolated `forest1` | Ran | All seven DB25 role/login pairs converged; 14 authentication/rotation and positive/negative permission checks passed; `uwa_runtime_login` passed production entrypoint, public API, exact sorted legacy payload, and aggregate `EMPTY` behavior with unchanged 126/195,457/86,895 and zero accounts/sessions. |
| GitHub/deploy preflight | GitHub / repository | Ran | Fork `main` is a 24-commit fast-forward ancestor of `5b358c1`; runner `wepp3` is online/idle with `deploy`; no queued/in-progress runs; `PRODUCTION_ENV` exists; `PRODUCTION_MIGRATION_ENV` and a configured production environment are absent. |
| Production privilege gate | `wepp3` | Ran | The operator temporarily installed and validated the exact passwordless-sudo boundary needed for protected files and the canonical service. It was removed after execution; subsequent `sudo -n` correctly failed. |
| Production migration and role convergence | `wepp3` | Ran | Under the canonical exclusive lock, additive migrations `0007`–`0011` completed in 36 seconds. Seven DB25 role/login pairs converged, runtime moved to `uwa_runtime_login`, migration uses `uwa_migration_login`, and schema/data state remained accepted. |
| Protected application deployment | `wepp3` | Ran | Exact target `5b358c1` deployed without replacing the database container, image, volume, or identity. The manual deploy passed, then fork `main` fast-forwarded without force and workflow run `29667975905` independently rebuilt, tested, and deployed the same source successfully. |
| Production verification | `wepp3` / public API | Ran | Unit, backup timers, Caddy, server, and unchanged database are healthy with zero restarts; ports 5432/8000 remain unbound; migration is `0011`; aggregates remain 126/195,457/86,895 and zero accounts/sessions; release state is `EMPTY`; canonical public payload SHA-256 remains `2770cf28...`. |
| Credential and resource cleanup | `wepp3` / `forest1` | Ran | Temporary sudo, scripts, staged environments, runner environments, containers, network, restored files, and rehearsal image tags were removed. Root-only pre-DB27A runtime credentials remain intentionally retained only for the proven exact-code rollback window; encrypted snapshot `08321397...` remains durable. |

### Findings and deviations

- The first read-only freeze stopped at the protected runtime file after
  confirming noninteractive sudo was unavailable; a follow-on used only
  non-secret Docker-visible values and did not bypass the protected file.
- The exact old application returns the same canonical GeoJSON payload after
  additive migration, although physical row order changes during table rewrite.
- Destructive disposable schema rollback cannot reproduce authentication
  metadata sequence positions because Django creates content types and
  permissions during forward migration; legacy Silk also writes request
  telemetry. DB27A's production rollback remains the rehearsed exact old code
  on the additive schema, not destructive schema reversal.
- The first production script invocation was a true no-op because a
  backgrounded lock wrapper could not consume the script from standard input.
  The script was staged as a protected file before retrying.
- The first protected retry built the application image but stopped at the
  credential guard because OpenSSL output files included a trailing newline.
  Only the reviewed role/ownership bootstrap had run; schema and serving
  runtime remained old and healthy. A root-owned Git index created during that
  attempt also prevented the scripted checkout reset. Ownership was corrected,
  unterminated credentials were regenerated, and execution resumed boundedly.
- Exact old code is compatible with the additive schema only when it uses its
  retained administrative runtime credential: under the new least-privilege
  runtime login, legacy Silk telemetry writes return HTTP 500. The old runtime
  file is therefore retained root-only at
  `/etc/utility-watershed-analytics/rollback/runtime.env.pre-db27a` for the
  accepted rollback window.
- The manual deployment briefly returned two HTTP 502 responses while the new
  server warmed, then passed its bounded retry and all subsequent verification.
- Deleting the temporary sudoers file intentionally removed privilege before
  the same shell could run its trailing `visudo` check. Independent follow-up
  confirmed the exact file is absent, noninteractive sudo is unavailable, the
  canonical unit is active, and the public schema route is healthy.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met; backup, rehearsal, migration, deployment,
  invariant verification, publication workflow, and cleanup all passed
- Blocker, if held: not applicable
- First follow-on action, if held: not applicable
- Successor package: DB28

## Artifacts

- `artifacts/db27a-validation-evidence.md`
- Local ignored administrative log under `docs/sys-administration/logs/`

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited production data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match authorization.
