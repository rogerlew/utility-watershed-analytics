# DB02 `wepp3` Production Identity and Reachability Evidence

Evidence mode: Ran unless marked Static

Environment: `wepp3` and `forest1`, 2026-07-17 America/Los_Angeles

Starting repository revision:
`61e1667e91986d3fba75155f6b473a200fa74141`

## Authority and boundary

The operator authorized the remaining DB02 read-only production identity and
reachability freeze. Inspection was bounded to runtime identity, principals,
listeners, observed firewall behavior, Compose labels, health, and backup
continuity. Repository changes and disposable `forest1` fixtures were allowed.

No production unit, container, network, volume, checkout, environment,
permission, group, socket, firewall, image, lock, or data was changed. No
Compose mutation, pull, build, migration, or reboot ran. Production adoption
remains DB03 work requiring explicit mutation authority.

## Host and exact database identity

- Host boot: `2026-07-17 04:02:36`; kernel `6.8.0-136-generic`.
- Docker: `29.6.2`; Compose: `v5.3.1`; Tailscale: `1.98.9`.
- Production public address: `129.101.202.225`; Tailscale address:
  `100.74.181.119`.
- Database container: `postgis`, ID
  `d2f0c406fc2bf02d5461b88d6f803112da1c9933494c2c6a68bf829268898bf2`.
- Image ID:
  `sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`.
- Frozen repository digest:
  `postgis/postgis@sha256:8896823da46b01b1ab5d3eaa9f29712e6bd8d00a7be965f5747fedbfd28d00c9`.
  The running configuration still names `postgis/postgis:latest`; DB02 does
  not authorize pulling or upgrading it.
- PostgreSQL: `17.5`; PostGIS: `3.5.2`.
- Compose project/service: `utility-watershed-analytics` / `db`; database
  config hash:
  `d5f1536963c5ab272b6a2a97621816b5c1341e5ef4eb31dc7f4670ae48c2ea44`.
- Data volume:
  `be7d3b8f6a3b08f300d2d3c45554e088eacce531a781d95bdff2fc9e32e22d51`,
  source `/var/lib/docker/volumes/<volume-id>/_data`, destination
  `/var/lib/postgresql/data`. It is an anonymous local volume created on
  2026-02-09.
- Database `pg4django` size: `27,791,576,211` bytes. Frozen representative
  counts: `126`, `195457`, and `86895` for the previously governed DB01
  verification queries.

The database was running and healthy with restart policy `no`. Its exact
container, image, labels, and mount remained unchanged throughout the read.

## Current split runtime origins

The running Compose project is assembled from two checkouts:

- `postgis` labels identify `/workdir/utility-watershed-analytics`, clean branch
  `rhessys-outputs-temp` at `b3114cc79d433d3b296dca27c78fa2fd06b56540`;
- `server` and `caddy` labels identify
  `/workdir/actions-runner/_work/utility-watershed-analytics/utility-watershed-analytics`,
  clean `main` at `28095c7b6620c187dfaa50c4d82d5a9eb2fdd359`.

Both label sets use project `utility-watershed-analytics` and network
`utility-watershed-analytics_default`. The network ID is
`e105f5efb6bdfd0b72c5798e501b14ff31d210f6e480d4905a8ecc844e91efa2`,
bridge subnet `172.17.0.0/16`; all three containers are attached.

The canonical checkout and Actions checkout have identical current
`compose.prod.yml` and `Caddyfile` hashes. The active checkout `.env` is owned
by `brandon:brandon`, mode `0664`, and contains 40 assignment keys. Values were
not read or recorded. DB03 must install a minimized root-owned mode-`0600`
runtime file instead of copying this broad file.

The legacy unit registration is `not-found` and
`/etc/systemd/system/utility-watershed-analytics.service` is absent. The unsafe
source remains in the production checkout with SHA-256
`fdec8821c894f62027782cf6257d0887183fbf0b896292caba92b0cf12bfd3e9`.
It contains `docker compose up`, `docker compose down`, and `Restart=always`;
it must not be installed or invoked. No reboot is authorized until DB03 has
installed and verified the canonical safe unit.

## Principals and lock inputs

- `roger`: UID `1002`; member of `sudo`, `docker` GID `998`, and `webgroup`.
- `gha`: UID `1012`; member of `sudo`, `docker` GID `998`, and `webgroup`.
- The self-hosted runner service is active as `gha`.
- The Docker socket is `root:docker`, mode `0660`.
- Target group `uwa-operators`, canonical lock directory, and canonical lock
  file do not exist.

These reads freeze the principal mapping. DB03 owns group membership, tmpfiles
installation, boot recreation, and real cross-principal contention tests;
DB02 did not make those host mutations.

## Reachability matrix

| Source | 80 | 443 | 5432 | 8000 | Evidence |
| --- | --- | --- | --- | --- | --- |
| `wepp3` localhost | open | open | open | open | Ran |
| `forest1` to `wepp3` Tailscale | open | open | open | open | Ran |
| `forest1` to `129.101.202.225` | open | open | closed | closed | Ran |
| Compose peers | Caddy path passed | Caddy path passed | server-to-db passed | Caddy-to-server passed | Ran |

All four services currently publish on all IPv4 and IPv6 host interfaces.
Public HTTP/HTTPS and the API returned success, while public 5432/8000 were
blocked. UFW was observed enabled and active, but exact root-only rule text was
not read. The behavior above, rather than an inferred rule set, is the DB02
firewall evidence.

The target render removes host publication for PostgreSQL and Django and keeps
only Caddy 80/443. DB03 may recreate only application-facing services to adopt
that target. It must not recreate `postgis` merely to remove port 5432 because
the database still uses an anonymous volume. Until DB05 moves that data under
a separately verified named-volume cutover, DB03 must preserve the exact
database container/mount and retain an explicit firewall denial for unwanted
non-Compose access.

## Fail-closed target verification

The repository target rendered with the frozen digest and proved:

- project `utility-watershed-analytics`;
- database/server Compose-only sockets and Caddy-only host ports 80/443;
- exact digest input resolving to the frozen production image ID contract;
- no fallback tag; and
- a minimized 13-key maximum runtime allowlist.

Inspection found that Compose `--no-recreate` alone can still create a missing
database. DB02 therefore added `scripts/start_runtime.sh` and fixtures. The
wrapper holds the exclusive canonical lock, validates protected runtime and
identity files, asserts the existing database before any Compose action,
resolves the pinned digest to the frozen image ID, rejects a dry run proposing
database creation or replacement, forbids build/pull/recreate, and reasserts
identity after start. Application-only deployment also uses `--pull never`.

Shell syntax, ShellCheck v0.10.0, lock fixtures, start-wrapper fixtures,
systemd verification, target render, unsafe-action scan, and whitespace checks
passed on `forest1`. No production action was used to obtain those results.

## DB03 adoption boundary

DB03 must begin from these exact identities, refresh them immediately before
mutation, and stop on drift. Its interim adoption must:

1. install the canonical group, lock, minimized environment, protected
   database-identity file, and safe unit without invoking the unsafe source;
2. prove real `roger`/`gha`/systemd lock contention and boot recreation;
3. inspect every Compose action and reject any `postgis` create, recreate,
   stop, remove, replacement, pull, project change, or mount change;
4. recreate only `server` and `caddy` as needed to remove host port 8000 and
   adopt the canonical checkout;
5. preserve the anonymous-volume database container while relying on the
   verified firewall boundary for port 5432 until DB05;
6. assert exact database identity before and after, smoke the application and
   reachability matrix, and exercise application-only rollback; and
7. run a successful locked off-host backup cycle afterward.

Final database Compose/systemd convergence remains DB05 work. DB02 made no
claim that the production bundle is installed.
