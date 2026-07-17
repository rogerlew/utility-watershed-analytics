# Wave 0 Environment Readiness

Status: **Ready for repository and database/API integration work; not ready
for complete full-stack or production execution**

Verified: 2026-07-16 on `forest1`

Repository revision:
`30a9077d432a5c8582759b614e0ea7224713b685`

Branch: `agent/database-backup-deployment-spec`, tracking the corresponding
origin branch with no locally observed divergence at verification time

## Scope and authority

This preflight determines whether the development environment can begin Wave 0
authoring. It does not scaffold or authorize a work package, establish that a
Wave 0 exit criterion has passed, or authorize access to production.

Environment roles are authoritative in [the deployment guide](../DEPLOYMENT.md):

- `forest1` is the shared development server.
- `wepp3` is the production server.

The initial environment commands ran on `forest1`. The user subsequently
authorized retrieving development environment inputs from `wepp3`. Over the
Tailscale network, SSH confirmed the remote hostname and read only the
environment-file path, metadata, variable names, and the two external
WEPPcloud token values. The local development file uses newly generated
database, pgAdmin, Django administrator, and Django secret values; no other
production value was copied.

No production container, database, service, or runtime state was inspected or
mutated. Production versions, identities, storage sizes, listeners, firewall
behavior, and runtime state therefore remain unverified for Wave 0 execution.

After the operator stopped the conflicting WEPPcloud development stack, ports
8000 and 5432 became available on `forest1`. The local database and API subset
was then started and checked. The unrelated `fswepp2-ui` service continues to
own port 5173 and was not disturbed.

## Observed readiness

| Check | Observation on `forest1` | Disposition |
| --- | --- | --- |
| Host identity | Hostname `forest1`; Ubuntu 24.04; systemd reports running. | Ready for development work. |
| Capacity | 48 CPUs, 188 GiB RAM with 57 GiB available, and 324 GiB free on the 938 GiB root filesystem at verification time. | Sufficient to start authoring and ordinary builds. Restore capacity remains unproven until production database and artifact sizes are measured. |
| Repository | Expected repository path, tracked working branch, and revision were present. Existing uncommitted authoring work was preserved. | Ready; work-package dispatch must freeze its own starting revision and mutation boundary. |
| Container tooling | Docker Engine 29.4.2 and Docker Compose v5.1.3 were usable by the development user. | Ready for isolated container work. |
| Configuration render | Development and production Compose files rendered successfully. The development render uses the protected local environment file. | Production remains static validation only. |
| Backup command | `scripts/backup_database.sh` is executable; `bash -n` and its help path passed. | Ready for repository iteration. ShellCheck was unavailable on the host and remains an applicable gate. |
| Development configuration | A development `.env` now contains newly generated local credentials plus the two explicitly authorized external token values from `wepp3`. It is owned by the development user, mode `0600`, ignored by `.gitignore`, untracked, and complete for the variables documented in the root README. The ignored `pgadmin-servers.json` file remains absent. | Environment interpolation is ready. Provide the ignored pgAdmin definition or exclude that optional service before starting the complete stack. |
| Development images | `docker compose build client server` built `utility-watershed-analytics-client` and `utility-watershed-analytics-server` successfully on `forest1`. | Ran build evidence. The server image is now running; the client image remains unstarted because its default host port is occupied. |
| Development stack | After ports 8000 and 5432 were released, the development PostGIS and Django services started from the local Compose project. Postgres reported healthy, every migration was applied, `manage.py check` reported no issues, and Django served an expected route-level 404 at the otherwise unmapped root URL. The running development database reported PostgreSQL 17.5 and PostGIS 3.5.2. | Ran evidence for the local database/API subset only. It is not evidence of production compatibility or a restore drill. |
| Development data seed | First-start loading attempted the configured WEPPcloud datasets but received HTTP 401. Both copied JWTs are structurally valid JWTs but expired before this preflight. The entrypoint reports the load failure and still starts Django. | Core database/API startup is usable, but dataset-dependent integration is blocked until development-scoped tokens are refreshed. Do not copy more production configuration by default. |
| Shared ports | After the operator stopped the conflicting WEPPcloud development stack, ports 8000 and 5432 were free and are now published by this project. Port 5173 remains published by the unrelated `fswepp2-ui` service; port 5050 is free. | Do not disturb `fswepp2-ui`. Use a non-conflicting client host port or an isolated no-publish topology before starting the client. |
| Backup destination | The default `/workdir/backups/utility-watershed-analytics` directory was absent, and `/workdir` is on the local root filesystem. | Superseded on 2026-07-16: DB01 accepted and provisioned `forest1:/wc1/utility-watershed-analytics-db-backups`. |
| Backup/encryption clients | GnuPG and OpenSSL were present; `age` and `restic` were absent. | Superseded on 2026-07-16: restic 0.16.4 was installed for the `roger` user and used for the accepted encrypted repository. |
| Host-side gates | ShellCheck and Ruff were not installed on the host. | Use the repository's containerized CI commands or install approved development tooling; do not record these gates as Ran until executed. |
| Production environment file | The authorized metadata read found `/workdir/utility-watershed-analytics/.env` on `wepp3` owned by `brandon:brandon` with mode `0664`. | Does not meet DB02's mode-`0600` target. No production permission or content was changed; remediate only in an authorized package. |

## Wave 0 execution update

After this preflight, the governed DB01 package passed an encrypted disposable
repository backup/restore chain on `forest1`: atomic archive creation, full
decode, checksums, restic publication/check, exact roles/extensions/migrations/
sequences/schema and 55-table comparison, and Django database/list API smoke.
The total development retrieval/restore/smoke duration was 26 seconds. Because
the expired WEPPcloud tokens left the development database without watershed
rows, this is empty-development evidence, not a production-shaped restore or an
accepted production RTO.

The operator later accepted and provisioned
`forest1:/wc1/utility-watershed-analytics-db-backups`, single-operator ownership,
a 24-hour RPO/RTO, and local journal alerts. Two encrypted snapshots, freshness,
retention, a 25-second restore, and the live daily/weekly user timer units passed.
Production transport remains outside this readiness record's authority.

The governed DB02 package also passed repository-side target runtime gates for
the shared/exclusive/inherited lock, minimized runtime environment, digest
requirement, Caddy-only host publication, application-only Compose dry run,
database identity assertion, systemd verification, workflow lint, 106 backend
tests, and a production server image build. Exact `wepp3` runtime identities and
reachability remain unverified and unauthorized.

The terminal package statuses and current unblock actions are authoritative in
the [work-package catalog](work-packages/README.md).

## Readiness judgment

`forest1` is ready to scaffold and execute the repository-only portions of DB01
and DB02. Their roadmap dependencies permit that work, Docker and systemd are
available, both Compose files can be inspected, the existing backup command has
a valid shell entry path, and the local database/API subset has now passed its
startup checks.

The environment is not yet ready to claim Ran evidence for the complete
client/API/database/pgAdmin stack, external-data integration, a non-empty
production-shaped restore, scheduled encrypted off-host backup, or production
runtime behavior. Before those claims are attempted:

1. Authorize DB01's bounded encrypted `wepp3`-to-`forest1` backup and isolated
   production-shaped restore drill without changing the serving production
   stack.
2. Retain the mode-`0600`, ignored development environment file and either
   provide the ignored pgAdmin definition or exclude pgAdmin from the test
   topology. Never commit or print its values.
3. Allocate a non-conflicting client development port or use a dedicated
   Compose project that does not publish ports to the shared host.
4. Obtain fresh development-scoped WEPPcloud tokens before recording external
   watershed loading as successful; never print token values in evidence.
5. Measure the source and backup sizes before accepting `forest1` as restore
   capacity, and use an isolated compatible PostGIS instance for the drill.
6. Obtain and record explicit read-only production authority before collecting
   the `wepp3` versions and identities required by DB02. Obtain separate
   mutation authority before any later convergence work.

The first recommended actions are the DB01 production-shaped drill and an
explicit read-only DB02 production identity freeze. This readiness record and
later development evidence do not authorize either action by themselves.
