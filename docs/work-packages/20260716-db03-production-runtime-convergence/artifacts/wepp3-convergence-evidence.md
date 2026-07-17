# DB03 `wepp3` Runtime Convergence Evidence

Evidence mode: Ran unless marked Static

Executed: 2026-07-17 America/Los_Angeles

Starting repository revision:
`61e1667e91986d3fba75155f6b473a200fa74141` plus preserved DB02 completion
changes.

## Authority and outcome

The operator authorized DB03's bounded `wepp3` production runtime mutation.
No reboot, database action, project change, image pull/upgrade, mount change,
data mutation, restore, named-volume work, commit, or push was authorized or
performed.

The host runtime convergence passed. The terminal package is held only because
the safe local deploy workflow is not yet committed/pushed to `main`; the old
remote workflow bypasses the canonical lock. The idle self-hosted runner was
therefore stopped and disabled so it cannot undo the accepted state.

## Protected database invariants

The database identity helper passed before and after target adoption, exercised
rollback, target reapplication, unit start/reload/stop/start, and final
closeout:

- container:
  `d2f0c406fc2bf02d5461b88d6f803112da1c9933494c2c6a68bf829268898bf2`;
- image:
  `sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`;
- project/service: `utility-watershed-analytics` / `db`;
- config hash:
  `d5f1536963c5ab272b6a2a97621816b5c1341e5ef4eb31dc7f4670ae48c2ea44`;
- anonymous volume:
  `be7d3b8f6a3b08f300d2d3c45554e088eacce531a781d95bdff2fc9e32e22d51`;
- mount destination: `/var/lib/postgresql/data`;
- final state: running, healthy, restart count zero; and
- final database size: `27,791,576,211` bytes.

PostgreSQL was never stopped, recreated, replaced, detached, remounted, or
passed to a mutating Compose command.

## Installed runtime

- Versioned scripts:
  `/usr/local/lib/utility-watershed-analytics-runtime/db03-20260717-61e1667/`
- Interim Compose file:
  `/workdir/utility-watershed-analytics/compose.db03.yml`, SHA-256
  `ee2ef4d081d58a8ff8159abf32a0e722e65fb81852f0344eba59d3402e46542b`
- Safe unit: `/etc/systemd/system/utility-watershed-analytics.service`,
  SHA-256
  `5a1940990733d52932e06e548a46691ff8ccae0556dce10b457798fc83bc81bc`
- Protected runtime and database identity: root-owned, mode `0600`.
- Legacy broad rollback environment: changed from `brandon:brandon` mode
  `0664` to `root:root` mode `0600`; values were never printed.
- Operations lock: root:`uwa-operators`, mode `0660`; parent mode `0770`.
- `uwa-operators`: `roger` and `gha`; refreshed user-manager and runner
  processes inherited the group.
- Tmpfiles contract installed at
  `/etc/tmpfiles.d/utility-watershed-analytics.conf`.

The runtime source `.env` repeated several required keys. Hash-only comparison
proved every repeated value identical. The first strict install failed closed;
the accepted protected file takes one identical value per key and passed the
13-key allowlist. No value or value hash is retained in this artifact.

The safe unit is enabled and active. Actual start, reload, application-only
stop, and start passed. During unit stop, server/Caddy stopped and PostgreSQL
remained running with unchanged identity. The unsafe checkout unit source was
not installed or invoked.

## Application convergence and rollback

The exact target dry run named only server/Caddy recreate/start. It named no
database action. Under the exclusive canonical lock, only those application
services were recreated using existing local images with no build or pull.

The former Actions-checkout configuration was then dry-run and applied as an
application-only rollback. It restored host port 8000 and passed health with
unchanged database identity. The target was dry-run and reapplied, again with
unchanged database identity and health. Final application identities are:

- server container:
  `f4085f6df928d44095565f9629eb52eb84d3a829e6c5a00dbbc5e8d0786be552`;
- server image:
  `sha256:4c5678dabc84a6b55e03b6c30b3bd2b4b591877f1682163ef6fcd56145c16139`;
- Caddy container:
  `692ae7268e520621fb40abf087bbf29aaf5ff8e0315872eee79ab55702f3e1dc`;
- Caddy image:
  `sha256:3aed261b9d04b08cca89b6076e336af590dbedcd5178dfd6d490cf26da61debf`.

Server and Caddy now label the canonical checkout. The server environment
contains the minimized runtime keys plus explicit `APP_ENVIRONMENT=production`
and no Django superuser seed variables.

## Lock and backup proof

Actual `roger`/`gha` processes passed:

- exclusive holder versus shared contender rejection;
- concurrent shared acquisition;
- TERM cancellation returning 143; and
- immediate exclusive reacquisition by the other principal.

The runner and the lingering `roger` user manager were restarted after group
provisioning and both inherited GID `996` (`uwa-operators`). The runner was
idle and healthy at that point.

The first post-adoption backup completed and published encrypted snapshot
`b1bb707c4897dba2f46ddc740b7209e284806fb80b14e8352f86845c1a6d06cb`,
but a live descriptor audit found DB01's protected environment still overrode
the wrapper default with its historical user-local lock. The archive remained
valid; it was not represented as canonical-lock proof.

Only that lock-path override was atomically removed from the mode-`0600`
backup environment. A second backup's live file descriptor pointed to
`/run/lock/utility-watershed-analytics/operations.lock`, and `gha` timed out on
exclusive acquisition while the backup held it shared. That backup completed,
verified, and published encrypted snapshot
`4361efe3befe74d24922cbd0b950790c0e87cc036c9be482f76177a0f60893a8`.
Freshness passed. `forest1` independently listed that exact snapshot with host
`wepp3` and tags `uwa-database,scheduled`.

## Socket and health matrix

| Source | 80 | 443 | 8000 | 5432 |
| --- | --- | --- | --- | --- |
| `wepp3` localhost | open | open | closed | open |
| `forest1` to Tailscale | open | open | closed | open |
| `forest1` to public IP | open | open | closed | closed |

Only Caddy publishes the application host sockets. Both obsolete UFW
`8000/tcp` allow rules were removed; a first numeric deletion removed IPv6 and
then failed harmlessly because the list renumbered, so the refreshed exact
IPv4 rule number was deleted on retry. Server-to-database TCP passed. A Caddy
raw request to the canonical host's admin login returned HTTP 200. Public root,
API, and canonical admin smoke passed.

PostgreSQL port 5432 remains host-published because removing it would recreate
the protected anonymous-volume database. Public access remains blocked;
localhost and the operator Tailscale remain open as an explicit DB05 residual.

## CI publication hold

The connected runner checkout's `main` still contains the old workflow that
creates a broad `.env`, bypasses the canonical lock, builds directly, and can
restore host port 8000. The safe repository workflow exists only in the current
uncommitted DB02/DB03 working tree. Commit and push were explicitly excluded.

The idle runner service was therefore stopped and disabled after its principal
and contention evidence passed. This does not affect serving or backup timers.
After the safe workflow and DB02/DB03 runtime files are committed and pushed to
the intended production branch, a bounded successor must refresh production
identity, confirm the checked-out workflow calls `scripts/deploy_application.sh`,
dry-run it against the installed contract, and enable/start the runner. Do not
reenable the old workflow.

Temporary passwordless sudo was removed at closeout and the remaining sudoers
configuration validated. No reboot occurred.

The later user-authorized commit/push publishes this evidence and the safe
workflow to `origin/agent/database-backup-deployment-spec`. That branch push
does not update the runner's `main` checkout or resolve the hold by itself.
