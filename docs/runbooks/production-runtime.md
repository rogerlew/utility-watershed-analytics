# Production Runtime Contract

Status: DB03 interim runtime installed; self-hosted deployment runner paused
until the safe workflow is committed and pushed

This contract defines the target production runtime without claiming it is
currently installed. `forest1` is development. `wepp3` is production and must
not be inspected or changed without the operation-specific authority recorded
in a work package.

## Canonical coordinates

- Checkout: `/workdir/utility-watershed-analytics`
- Compose project: `utility-watershed-analytics`
- Interim installed Compose file:
  `/workdir/utility-watershed-analytics/compose.db03.yml`
- Final repository Compose target:
  `/workdir/utility-watershed-analytics/compose.prod.yml`
- Runtime environment: `/etc/utility-watershed-analytics/runtime.env`, owned by
  root, non-symlink, mode `0600`
- Database identity:
  `/etc/utility-watershed-analytics/database-identity`, owned by root,
  non-symlink, mode `0600`
- Systemd unit: `utility-watershed-analytics.service`
- Operations lock:
  `/run/lock/utility-watershed-analytics/operations.lock`, owned by
  `root:uwa-operators`, mode `0660`

The self-hosted Actions checkout is a build/dispatch workspace, not the
canonical long-lived runtime. DB03 moved server/Caddy labels to the canonical
checkout under the existing project without changing the database identity.
The unsafe unit source remains in the checkout as evidence and is not
installed. The safe `/etc` unit is enabled and active. Exact sanitized DB03
evidence is in
[`wepp3-convergence-evidence.md`](../work-packages/20260716-db03-production-runtime-convergence/artifacts/wepp3-convergence-evidence.md).

## Target socket contract

| Service | Compose access | Host publication | Intended reachability |
| --- | --- | --- | --- |
| Caddy | ports 80 and 443 | public 80/443 | public and operator paths allowed by host firewall |
| Django server | `server:8000` | none | Compose peers only through Caddy |
| PostgreSQL | `db:5432` | none | Compose peers and `docker exec`; no localhost, Tailscale, or public socket |
| Frontend build | one-shot volume writer | none | no network listener |

DB03 must test this matrix from a Compose peer, localhost, the `wepp3`
Tailscale address, and the public interface and record firewall assumptions.
Unexpected application host publication is a hold. The DB03 interim preserves
the exact anonymous-volume database, so its old host publication remains open
on localhost and the operator Tailscale while public access is blocked. DB05
must remove that residual during the separately backed-up named-volume cutover;
do not harden it now by recreating the database container.

## Exact database image

`POSTGIS_IMAGE` has no fallback and must use a repository digest:

```text
postgis/postgis@sha256:<64 lowercase hexadecimal characters>
```

An authorized read-only identity freeze must record the running container ID,
image ID and repository digest, PostgreSQL/PostGIS versions, Compose project,
config hash, checkout, data-volume name/source/destination, and unit text.
Resolve the running image ID to its existing repository digest without pulling
a newer tag. DB02 does not authorize an upgrade.

Before production adoption, capture the current database boundary with
`scripts/database_identity.sh capture` and install the sanitized result as the
protected database-identity file. The pinned rendered image must resolve
locally to the same image ID. `scripts/start_runtime.sh` and
`scripts/deploy_application.sh` assert that identity before and after their
actions; the deployment helper additionally captures its own operation-local
copy. Container, image, project labels, and data mount must remain
byte-for-byte identical.

## Runtime environment

Start from `ops/runtime/runtime.env.example`. The accepted installed file may
contain only:

- exact `POSTGIS_IMAGE`;
- PostgreSQL database/user/password;
- Django secret key;
- the two current WEPPcloud tokens; and
- optional Gunicorn tuning values.

It must not contain Django superuser seed values, backup credentials, webhook
URLs, unrelated application settings, or the complete GitHub secret context.
`scripts/check_runtime_environment.sh` rejects symlinks, wrong ownership,
wrong mode, empty/duplicate/unknown keys, missing required keys, carriage
returns, and an unpinned image.

The Actions workflow creates `.env.production-runtime` with `umask 077`,
validates it, and shreds it in an `always()` cleanup step. A cancelled runner
must still be audited for a leftover file before its next job.

## Host-wide lock

DB03 installed the operator group and boot-time tmpfiles contract:

```bash
sudo groupadd --system uwa-operators
sudo install -o root -g root -m 0644 \
  ops/tmpfiles.d/utility-watershed-analytics.conf \
  /etc/tmpfiles.d/utility-watershed-analytics.conf
sudo systemd-tmpfiles --create utility-watershed-analytics.conf
```

`roger` and `gha` are members of `uwa-operators`; the system unit runs as root.
DB03 refreshed the lingering user manager and runner context, then passed real
cross-principal contention, cancellation, and reacquisition. Membership grants
authority to contend for the lock, not authority to perform a production
operation.

Use `scripts/with_operation_lock.sh`:

- exclusive: application deploy, migrations, data activation, restore, volume
  work, recovery, retention prune, and legacy mutation;
- shared: scheduled/on-demand logical backup, backup freshness, periodic
  isolated restore test, and explicitly approved read-only operations.

The outer orchestrator holds one open descriptor for its entire lifetime.
Nested commands inherit the descriptor and mode; an exclusive deploy may call a
shared backup without reacquiring, while a shared operation cannot upgrade to
exclusive. Acquisition has a bounded timeout. TERM/INT forwards to the child,
the descriptor closes, and the next operator must reassert protected state
before continuing.

Do not delete or replace the lock file to clear contention. Identify the
holder, stop it through its supported cancellation path, verify its child and
database state, and then acquire the same inode normally.

## Canonical systemd behavior

The tracked unit:

- requires the root-owned runtime and protected database-identity files;
- takes one exclusive host lock across the entire start;
- asserts exact database identity before and after Compose;
- resolves the pinned database digest to the expected local image ID;
- dry-runs and rejects database create or replacement actions;
- starts existing images with `--no-build --no-recreate --pull never`;
- reloads only `server` and `caddy` with `--no-deps --pull never`; and
- stops only `server` and `caddy`.

There is no `docker compose down` path and no systemd stop action for the
database. Host shutdown ultimately stops Docker, but ordinary unit stop/reload
preserves the database container and anonymous-volume reference.

DB03 installed the reviewed interim unit directly in `/etc` without installing
or invoking the unsafe checkout source. Start, reload, application-only stop,
and start passed with unchanged PostgreSQL identity. Never replace it with the
unsafe source.

## Application deployment

The repository target uses one non-cancelling production concurrency group and
calls `scripts/deploy_application.sh`. The script:

1. acquires or verifies an inherited exclusive host lock;
2. validates the minimized mode-`0600` runtime environment;
3. captures exact database identity;
4. renders Compose and verifies the digest resolves to the running image ID;
5. dry-runs only `server` and `caddy` and rejects a database action;
6. builds application/frontend images;
7. runs Django migrations explicitly in a one-off container;
8. rebuilds frontend static output and replaces only server/Caddy;
9. reasserts exact database identity; and
10. runs the configured HTTPS health check.

Production execution additionally requires DB01 completion, a fresh backup
when the migration plan requires it, reviewed migration compatibility, current
base identity, and package-specific authority. The server entrypoint may keep
`migrate` as a safety check, but it is not the deployment's migration evidence.

The production runner is intentionally disabled because its current `main`
checkout still contains the old workflow that bypasses this lock and can
re-expose port 8000. Do not reenable it until the safe workflow and runtime
helpers are committed and pushed to the intended branch, the runner checkout
is verified, and a bounded enable/start check is authorized.

## Interim adoption and rollback

DB03 executed the interim command set against refreshed observed identities:

1. capture the original unit, checkout, project, containers, images, networks,
   mounts, and volume identity;
2. inspect every proposed Compose action and fail on database create,
   recreate, replace, stop, remove, rename, project change, or mount change;
3. preserve the absent unsafe registration and install only the safe unit;
4. provision the lock, protected minimized environment, and protected exact
   database-identity file;
5. update only application services with `--no-deps`;
6. prove database identity and application smoke before/after; and
7. run a successful scheduled off-host backup under the adopted lock.

The target, exercised application-only rollback, target reapplication, safe
unit cycle, and canonical locked backup all passed with unchanged database
identity. If any future identity differs, stop the proposal and restore only
the application path under the lock. Do not invoke `down`, attach a new volume,
or attempt final database Compose convergence. That convergence belongs to
DB05's separately backed-up and exercised cutover.

## Verification matrix

DB02 repository evidence may prove renders, static socket declarations,
lock nesting/contention/cancellation, environment rejection, database identity
capture/assert, unit syntax, and application-only dry-run behavior on
`forest1`.

DB03's authorized `wepp3` evidence now proves:

- current image/project/unit/container/volume identity;
- actual operator/systemd/runner group contention;
- localhost/Tailscale/public/firewall reachability;
- safe loaded-unit start/reload/application-only stop/start behavior; and
- application deployment/rollback with unchanged production database identity.

No reboot was authorized or claimed.
