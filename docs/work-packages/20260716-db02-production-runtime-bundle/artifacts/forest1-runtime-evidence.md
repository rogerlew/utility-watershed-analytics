# DB02 Repository and Isolated Runtime Evidence

Evidence mode: Ran unless marked Static

Environment: `forest1`, 2026-07-16 America/Los_Angeles

Starting revision:
`30a9077d432a5c8582759b614e0ea7224713b685` plus preserved Wave 0 and DB01
working-tree changes

No `wepp3` host, production runtime, firewall, container, image, volume, unit,
principal, or socket state was inspected or changed for these checks.

## Host lock

`scripts/tests/test_operation_lock.sh` used a disposable regular lock file and
separate processes:

- exclusive outer lock with nested shared operation: passed;
- exclusive outer lock with nested exclusive operation: passed;
- shared outer to nested exclusive upgrade: rejected;
- exclusive holder versus shared contender with bounded timeout: rejected;
- two concurrent shared holders: passed;
- TERM cancellation: wrapper returned 143;
- immediate exclusive reacquisition after cancellation: passed; and
- closed/stale inherited descriptor: rejected.

The tmpfiles contract statically specifies parent mode `0770`, lock mode `0660`,
and `root:uwa-operators`. It was not installed because the group and root
authority are intentionally absent from the local package boundary.

## Runtime environment

`scripts/check_runtime_environment.sh` passed a mode-`0600`, current-user-owned,
seven-key minimized fixture containing only required runtime keys and an exact
development fixture digest.

- mode `0644`: rejected;
- extra Django superuser password key: rejected;
- unpinned `POSTGIS_IMAGE`: rejected; and
- required-key, duplicate-key, empty-value, symlink, owner, and allowlist checks
  are implemented and ShellCheck-clean (Static where not separately injected).

No values from the real ignored development environment are preserved here.

## Compose and database identity

A non-production digest render of `compose.prod.yml` passed:

- only Caddy published host sockets;
- published target ports were exactly 80 and 443;
- server port 8000 and PostgreSQL port 5432 were Compose-only;
- `APP_ENVIRONMENT=production` rendered for Django;
- database image required and rendered a repository digest; and
- app-only `docker compose --dry-run up --no-deps server caddy` proposed no
  database create, recreate, remove, stop, or replace action.

`scripts/database_identity.sh` captured and reasserted the running development
container, image, Compose labels, and anonymous data mount. A tampered expected
container ID was rejected. This proves the comparison tool, not production
identity.

The tracked systemd unit has:

- a runtime environment precheck;
- canonical checkout, project, environment, and Compose file coordinates;
- exclusive lock wrapping start/reload/stop;
- `--no-build --no-recreate` start;
- application-only `--no-deps` reload; and
- application-only stop of `server` and `caddy`.

A source scan found no `compose down`, database stop, or database remove path
in the unit, deployment workflow, or application deployment orchestrator.

## Gates

- `bash -n` for all shell scripts: passed.
- ShellCheck v0.10.0 for all shell scripts and lock tests: passed.
- Actionlint v1.7.7: passed while ignoring only the repository's intentional
  custom self-hosted runner label `deploy`.
- `systemd-analyze verify` for the application unit and all backup units/timers:
  passed. One unrelated warning remains for executable host file
  `/etc/systemd/system/docker-compose-fswepp2.service`.
- `docker compose config` production target render with explicit development
  fixture digest: passed.
- Ruff full backend gate: passed.
- Django full backend suite: 106 tests passed.
- Production server image build: passed; local test image ID
  `sha256:4724859b05f6013171335dc804d4e239590d5a4717480ac397d26b696f8a042f`.
- `git diff --check`: recorded in final orchestration gates.

## Unmet DB02 completion evidence

- exact currently running production PostGIS repository digest and versions;
- production checkout, Compose project/config hash, containers, networks,
  image IDs, anonymous-volume name/source/destination, and loaded unit;
- safe interim actions derived from those identities;
- real operator, systemd, and CI runner group ownership/contention;
- unit start/stop/reload, signal, cancellation, reboot, and rollback on `wepp3`;
- Compose-peer, localhost, Tailscale, public, and firewall reachability matrix;
- before/after production identity preservation; and
- DB01 completion and successful scheduled off-host backup after adoption.
