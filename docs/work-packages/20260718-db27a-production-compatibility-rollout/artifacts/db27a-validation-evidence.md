# DB27A validation evidence

Date: 2026-07-18

Environment: `forest1` development/rehearsal and authorized bounded `wepp3`
production schema/application rollout.

Starting revision: `5b358c1` on
`agent/database-backup-deployment-spec`.

Evidence mode: Mixed. This record will distinguish executed host/database/API
checks from static source and contract review. It contains only sanitized
aggregate results and identifiers; credentials, environment files, raw dumps,
database globals, and production rows remain outside Git.

## Authority and scope

The operator authorized DB27A scaffolding and execution on 2026-07-18. The
bounded operation covers a fresh encrypted `wepp3` backup to
`forest1:/wc1`, isolated rehearsal, additive compatibility migrations, DB25
role convergence, dual-compatible code deployment, and invariant verification.
It excludes data release adoption/activation, destructive production rollback,
database engine/volume changes, reboot, unrelated host work, and DB27A
publication.

## Results

### Production baseline and fresh backup

Read-only `wepp3` inspection found the clean fork-owned `main` checkout at
`ae74c39...`, the enabled/active canonical unit and lock, healthy named database
volume, PostgreSQL 17.5/PostGIS 3.5.2 image ID `612b68f8...`, and exact serving
image ID `4c5678da...`. The database is at watershed migration `0006` with 126
watersheds, 195,457 subcatchments, 86,895 channels, and zero accounts/sessions.
No DB25 `uwa_*` roles are installed. Public schema and watershed routes returned
HTTP 200; release status correctly remains absent before compatibility rollout.

The existing shared-lock scheduled backup completed successfully. It produced
a 1,217,146,341-byte locally verified archive with SHA-256 `78c866c4...` and
published encrypted restic snapshot
`08321397dfb6c92b89e2d6e2aa21760b4bc73e6db8417cd75b2b60953b8ef03f` to the
accepted `forest1:/wc1` repository. Independent `forest1` listing and a restic
metadata plus 1/100 data-pack subset check found no errors.

### Production-shaped rehearsal

The exact fresh snapshot restored into an isolated exact-image PostGIS target
in 351 seconds. Source roles/memberships, extensions, migrations, sequences,
schema, and every table fingerprint matched.

The first additive forward applied migrations `0007` through `0011` in 35
seconds. The exact pre-rollout server image ID `4c5678da...` ran successfully on
that schema and returned the same field-complete sorted 126-feature GeoJSON
SHA-256 `2770cf28...` as before migration. The current image ID `1b6c0b59...`
proved normal startup uses `migrate --check`, compatibility reported migration
`0011` with state `EMPTY`, and the aggregate release-status endpoint returned
HTTP 200 without release or attempt details.

A disposable-only schema rollback to `0006` completed in 26 seconds. Watershed
fingerprints, migration set, and extensions returned exactly; Django
content-type/permission sequence positions and live legacy Silk telemetry did
not. This proves why DB27A's production rollback boundary is the exact old code
on retained additive schema rather than a destructive migration reversal. The
old schema endpoint and sorted watershed payload remained exact.

The second forward used a bootstrapped `uwa_migration_login` and completed in
32 seconds. All seven DB25 privilege/login pairs converged, and 14 credential
rotation plus allowed/denied permission probes passed. A separately rotated
`uwa_runtime_login` passed the production migration-check-only entrypoint,
schema, watershed, and `EMPTY` status routes. Final aggregates remained
126/195,457/86,895 with zero accounts/sessions and an empty active pointer.

### Production rollout

The operator temporarily installed and validated the exact passwordless-sudo
boundary required for the protected files and canonical service. The first
standard-input script attempt made no changes because the backgrounded lock
wrapper could not consume the remaining input. A protected staged retry built
the target image, bootstrapped only reviewed role ownership, and then stopped
safely when the credential guard detected a trailing newline in OpenSSL output.
Schema remained at `0006`, the old runtime remained healthy, and no checkout or
public-serving change had occurred. A root-owned Git index from that attempt
also blocked the scripted checkout reset; ownership was corrected before the
bounded resume.

With unterminated credential files, the resume held the canonical exclusive
lock, applied migrations `0007` through `0011` once in 36 seconds, converged all
seven DB25 privilege/login pairs, installed root-owned mode-`0600` runtime and
migration environments, and moved ordinary runtime access to
`uwa_runtime_login`. Migrations use the distinct `uwa_migration_login`.
Application deployment passed after two transient warm-up HTTP 502 responses.
The production database container ID `f315e224...`, image ID `612b68f8...`,
named volume, and database identity remained unchanged.

Exact old code under the new runtime login returned HTTP 500 because its legacy
Silk middleware writes telemetry. The exact old image remains compatible with
the additive schema when using its pre-rollout administrative credential, so a
single root-only mode-`0600` copy is intentionally retained at
`/etc/utility-watershed-analytics/rollback/runtime.env.pre-db27a` for the
accepted rollback window. Production destructive schema rollback remains
excluded.

### Publication workflow and final verification

The protected repository secrets `PRODUCTION_ENV` and
`PRODUCTION_MIGRATION_ENV` were updated without exposing values. Fork `main`
fast-forwarded without force from `c9ab4c9` to exact reviewed target `5b358c1`.
Push workflow run `29667975905` completed successfully: server, client, data
contract, and protected deploy jobs all passed. No data-release workflow was
dispatched, and no queued or running workflow remained.

Production is clean on fork `main` at `5b358c1`. The final workflow-built
server image is `f62e7422...`; server, Caddy, and the unchanged database are
running with zero restarts. The canonical unit is active/enabled, backup and
freshness timers are active, and host ports 5432 and 8000 are not listening.
Public schema, watershed, and release-status routes return HTTP 200. The
canonical sorted watershed payload SHA-256 remains `2770cf28...`; release
status is `EMPTY` with no active release. Legacy-empty capability responses
match the reviewed RHESSys/SBS behavior, including unavailable behavior for an
unknown run.

The final database is at migration `0011_capability_runtime_types` with 126
watersheds, 195,457 subcatchments, 86,895 channels, zero accounts, zero
sessions, 126 non-null distinct logical watershed identities, and no active
release. The accepted role signature is `b743c887...`, columns signature is
`73427230...`, and constraints signature is `71b2b2cf...`. The 14 DB25 roles
plus the retained legacy DB05 restore administrator are present; normal runtime
uses the least-privilege login.

### Cleanup

Disposable `forest1` PostGIS, network, restore files, and imported rehearsal
image tags were removed. Production staging scripts and transient environment
files were removed, and the runner workspace contains no generated deployment
environment. Encrypted snapshot `08321397...` remains in the authorized
`forest1:/wc1` repository. The exact temporary sudoers file was deleted;
because privilege disappeared immediately, the same combined shell could not
run its trailing `visudo` command. Independent follow-up confirmed the file is
absent, `sudo -n` is unavailable, the unit is active, and the public schema
route is healthy. No release adoption, activation, data workflow, reboot,
engine upgrade, or volume change occurred.
