# Deployment Guide
This document provides information on how the Utility Watershed Analytics application is deployed in a production environment and provides guidelines for maintaining and managing the setup.

## Environment Roles

| Hostname | Role | Use and authority boundary |
| --- | --- | --- |
| `forest1` | Shared development server | Repository authoring, builds, tests, and explicitly isolated non-production rehearsals. Other projects share this host, so verify ports, storage, and service names before use. Results observed here do not establish production state. |
| `wepp3` | Production server | Runs the public application and production data. Read-only inspection and mutation each require explicit production authority; repository approval alone is insufficient. |

Unless a section explicitly says otherwise, production commands and host facts
in this guide apply to `wepp3`. Never run a production command merely because
the repository and `compose.prod.yml` are available on `forest1`.

Database backup, retention, restore testing, maintenance, disaster recovery,
and selective restore follow the governed
[database backup and restore runbook](docs/runbooks/database-backup-restore.md).
The runbook is a repository contract, not standing production authority.

## Production Hosting Environment
The application is deployed on a virtual machine (VM) provided by the [University of Idaho's Research Computing and Data Services (RCDS)](https://hpc.uidaho.edu/index.html).

**Server Details:**
* **Hostname:** wepp3
* **OS:** Ubuntu 24.04.2 LTS
* **Virtualization:** VMware
* **Public Domain:** `unstable.wepp.cloud`

## CI/CD Overview

Deployments are automated via **GitHub Actions** with a self-hosted runner on the production VM.

### Workflow Summary

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `client-ci.yml` | PR to `main` (client changes) | Build & test frontend |
| `server-ci.yml` | PR to `main` (server changes) | Build & test backend |
| `deploy.yml` | Push to `main` | Build & deploy to production |

### Automatic Deployment

When code is pushed to the `main` branch:

1. **CI checks run** - Server and client CI workflows validate the build
2. **Deploy job starts** - Runs on the self-hosted runner on the production VM
3. **Environment setup** - Creates a mode-`0600`, allowlisted runtime file from
   GitHub secrets (`PRODUCTION_ENV`)

> **Note:** The `PRODUCTION_ENV` secret must include:
> - `WEPPCLOUD_JWT_TOKEN` – JWT for the nasa-roses-2026-sbs batch (required).
> - `WEPPCLOUD_JWT_TOKEN_2` – Current JWT for the victoria-ca-2026-sbs batch (required).
>
> Both batches are loaded in a single `load_watershed_data` or `download_data` run. Contact the project maintainer to obtain tokens.
4. **Serialized deployment** - Acquires the canonical host lock, freezes the
   database identity, and rejects an unpinned image or database action
5. **Explicit migration and build** - Runs migrations, rebuilds the server and
   frontend, and replaces only server/Caddy
6. **Identity and health checks** - Reasserts the unchanged database container,
   image, project, and volume, then checks the HTTPS endpoint
7. **Cleanup** - Shreds the temporary runtime file even after failure

### Manual Deployment

You can also trigger deployment manually from the GitHub Actions UI:

1. Go to **Actions** → **Build & Deploy Client/Server**
2. Click **Run workflow** → Select `main` branch → **Run workflow**

## Production Architecture

The production deployment consists of four main services orchestrated with Docker Compose:

1. **Frontend Build** - Builds React static files into a shared volume
2. **Backend (Django)** - API server running with Gunicorn
3. **Database (PostgreSQL + PostGIS)** - Geospatial database
4. **Reverse Proxy (Caddy)** - Serves static frontend files and proxies API requests

The frontend React application is built in a dedicated container that outputs static files to a shared Docker volume. Caddy serves these static files directly while proxying API routes (`/api/*`, `/admin/*`, `/silk/*`) to the Django backend.

The backend runs with configurable Gunicorn process/thread concurrency via environment variables in `compose.prod.yml`:

- `GUNICORN_WORKERS` (default `8`)
- `GUNICORN_THREADS` (default `2`)
- `GUNICORN_TIMEOUT` (default `180`)
- `GUNICORN_KEEPALIVE` (default `5`)
- `GUNICORN_MAX_REQUESTS` (default `2000`)
- `GUNICORN_MAX_REQUESTS_JITTER` (default `200`)

Set these in the protected minimized runtime environment derived from the
GitHub `PRODUCTION_ENV` secret. The complete contract, lock behavior, and
adoption boundary are defined in the
[production runtime runbook](docs/runbooks/production-runtime.md).

To ensure the Docker Compose stack autostarts on VM reboot, a [systemd service](utility-watershed-analytics.service) is configured on the host VM.

## Server Access & Manual Operations

For tasks that require direct server access (data management, debugging, etc.):

### Accessing the Server
SSH into the VM using your RCDS-provided credentials:
```bash
ssh your_netid@unstable.wepp.cloud
```
> You may need to connect to a VPN or authenticate to a firewall first.

### Project Location

The canonical long-lived production checkout target is:

```bash
cd /workdir/utility-watershed-analytics
```

The self-hosted runner checkout is a transient build/dispatch workspace, not
the runtime identity. DB03 must reconcile the observed current checkout with
this target without changing the database container or anonymous volume.

## Data Management

Data loading is **not automated** by CI/CD and must be done manually when data updates are needed.

The loader uses a **local-first approach**: it checks for cached files first, then falls back to fetching from remote URLs.

For every separately authorized legacy data-management shell, define the exact
runtime coordinates once:

```bash
production_compose=(
  docker compose
  --project-name utility-watershed-analytics
  --env-file /etc/utility-watershed-analytics/runtime.env
  --file /workdir/utility-watershed-analytics/compose.prod.yml
)
```

### Running Long Data Operations

Data loading can take a significant amount of time. Use `tmux` to run commands in a persistent session that survives SSH disconnections:

```bash
# Start a new tmux session
tmux new -s data-load

# Run your data loading command inside tmux
cd /workdir/utility-watershed-analytics
scripts/with_operation_lock.sh --mode exclusive -- \
  docker compose --project-name utility-watershed-analytics \
  --env-file /etc/utility-watershed-analytics/runtime.env \
  --file compose.prod.yml exec server python manage.py load_watershed_data

# Detach from session: Press Ctrl+B, then D
# You can now safely disconnect from SSH

# Later, reattach to check progress
tmux attach -t data-load
```

### Download Data Files (Optional)

Pre-download data files to avoid repeated network fetches when initially loading
an empty database. Downloaded files are cached in the named Docker volume
`watershed_data` (mounted at `/data` in the server container). The current
command skips every existing filename without checking a source revision or
checksum; remove or replace stale cache entries only under an approved runbook.

```bash
# Download ALL production data (recommended for production)
"${production_compose[@]}" exec server python manage.py download_data --all
```

Do not use `download_data --runids` for the NASA batch in the current
implementation. Its custom master filename is incorrectly treated as the batch
identifier, so matching NASA run IDs are silently skipped. Use `--all` under an
approved initial-load runbook until the filter is corrected and regression
tested.

### Load Data into Database

The commands below are legacy initial-load tools for an empty database. They do
not reconcile a populated production database and must not be used as a routine
update procedure. `APP_ENVIRONMENT=production` rejects every `--force` use
before querying or deleting watershed rows. Production also omits the Silk app,
middleware, and `/silk/` route so request and response capture cannot grow.

```bash
# Load ALL watersheds (production - discovers all from API)
"${production_compose[@]}" exec server python manage.py load_watershed_data --all

# Load specific watersheds by runid
"${production_compose[@]}" exec server python manage.py load_watershed_data --runids <runid1> <runid2>

# Load development subset only (defaults if no args provided - testing only)
"${production_compose[@]}" exec server python manage.py load_watershed_data

# Print the selected configuration only; this does not fetch or validate data
"${production_compose[@]}" exec server python manage.py load_watershed_data --dry-run
```

### Complete Data Setup (Download + Load)

For an initial empty-database load only:

```bash
# 1. (Optional) Pre-download all production data files to avoid network fetches
"${production_compose[@]}" exec server python manage.py download_data --all

# 2. Load all watershed data into database
"${production_compose[@]}" exec server python manage.py load_watershed_data --all
```

**Note:** The download step is optional—the loader will fetch from remote URLs
if cached files are unavailable. This workflow is not safe for updating a
populated production database.

### Major Schema or Data Source Updates

Do not use `docker compose down` as a routine production data-update procedure.
The loader now rejects `--force` in production. Outside production, `--force`
requires `--all`; combining it with `--runids` or relying on the default subset
is rejected before the database is queried. PostgreSQL currently uses an
anonymous volume, and an older deployed loader can delete all watershed rows
before replacement loading, so do not treat the repository guard as active on
a host until a separately authorized application deployment is verified.

The proposed reproducible release, reconciliation, validation, and rollback
workflow is specified in
[docs/database-deployment-architecture.md](docs/database-deployment-architecture.md).
Until that tooling is implemented, every production data-source change requires
an individually reviewed runbook, a newly verified off-host backup, validation
in an isolated database, explicit expected additions/removals/counts, and
post-change API verification. Adding a named volume also requires a controlled
backup/restore cutover; merely adding the Compose mount would start an empty
database.

## Useful Commands

```bash
# View service logs
docker compose --project-name utility-watershed-analytics \
  --env-file /etc/utility-watershed-analytics/runtime.env \
  --file compose.prod.yml logs -f [service_name]

# Check service status
docker compose --project-name utility-watershed-analytics \
  --env-file /etc/utility-watershed-analytics/runtime.env \
  --file compose.prod.yml ps

# Stop application-facing services only; never use compose down
sudo systemctl stop utility-watershed-analytics.service

# Start existing images without recreating containers
sudo systemctl start utility-watershed-analytics.service

# Reconcile application services only under the canonical lock
sudo systemctl reload utility-watershed-analytics.service
```

## Troubleshooting

### Deployment Failed
Check the GitHub Actions logs for the failed workflow run. Common issues:
- Docker build failures
- Missing environment secrets
- Service health check failures

### Services Not Starting
```bash
# Check container status and logs
docker compose --project-name utility-watershed-analytics \
  --env-file /etc/utility-watershed-analytics/runtime.env \
  --file compose.prod.yml ps
docker compose --project-name utility-watershed-analytics \
  --env-file /etc/utility-watershed-analytics/runtime.env \
  --file compose.prod.yml logs server
```

### Database Issues
```bash
# Check database connectivity
docker compose --project-name utility-watershed-analytics \
  --env-file /etc/utility-watershed-analytics/runtime.env \
  --file compose.prod.yml exec server python manage.py check

# Migrations run through the locked deployment orchestrator, not ad hoc
scripts/deploy_application.sh \
  --env-file /etc/utility-watershed-analytics/runtime.env \
  --healthcheck-url https://unstable.wepp.cloud/api/schema/
```

## Acknowledgements
Thanks to the University of Idaho RCDS team for hosting support.
