# DB03 `wepp3` Interim Adoption and Rollback Plan

Evidence mode: Mixed

Reviewed: 2026-07-17 America/Los_Angeles

Starting repository revision:
`61e1667e91986d3fba75155f6b473a200fa74141` plus preserved DB02 completion
changes.

## Protected invariants

The following complete identities must match immediately before and after each
application action:

- database container
  `d2f0c406fc2bf02d5461b88d6f803112da1c9933494c2c6a68bf829268898bf2`;
- database image
  `sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`;
- repository digest
  `postgis/postgis@sha256:8896823da46b01b1ab5d3eaa9f29712e6bd8d00a7be965f5747fedbfd28d00c9`;
- Compose project/service `utility-watershed-analytics` / `db` and frozen
  config hash; and
- anonymous volume
  `be7d3b8f6a3b08f300d2d3c45554e088eacce531a781d95bdff2fc9e32e22d51`
  mounted at `/var/lib/postgresql/data`.

Any mismatch is an immediate stop. No database Compose action is permitted.

## Install coordinates

- Versioned scripts:
  `/usr/local/lib/utility-watershed-analytics-runtime/db03-20260717-61e1667/scripts/`
- Interim Compose target:
  `/workdir/utility-watershed-analytics/compose.db03.yml`
- Protected runtime:
  `/etc/utility-watershed-analytics/runtime.env`
- Protected identity:
  `/etc/utility-watershed-analytics/database-identity`
- Lock/tmpfiles:
  `/run/lock/utility-watershed-analytics/operations.lock` and
  `/etc/tmpfiles.d/utility-watershed-analytics.conf`
- Unit: `/etc/systemd/system/utility-watershed-analytics.service`, sourced
  exactly from `wepp3-interim-runtime.service`

The unsafe checkout unit is retained as evidence and is never installed.
The existing tracked `compose.prod.yml` is not overwritten. DB05 owns final
checkout/Compose convergence.

## Reviewed action sequence

1. Refresh the protected invariants, current application/Caddy identities,
   backup readiness, and health.
2. Install the versioned scripts and new interim Compose filename. Create
   `uwa-operators`, add `roger` and `gha`, install tmpfiles, and recreate the
   user/runner execution contexts so future processes inherit the group.
3. Derive the minimized root-owned runtime file directly from the existing
   production environment without printing values. Replace the database image
   input with the frozen repository digest. Validate the 13-key allowlist.
4. Capture the protected database identity, render the interim target, verify
   the digest resolves to the frozen image ID, and dry-run application-only
   adoption. Reject any output naming a database action.
5. Under the exclusive canonical lock, recreate only `server` and `caddy` with
   `--no-build --no-deps --pull never`. Assert database identity and smoke.
6. Exercise rollback under the same lock with the Actions checkout's original
   Compose file and the retained root-protected legacy rollback environment;
   assert identity and smoke. Then reapply the interim target and assert again.
7. Remove only the obsolete UFW allow rules for host port 8000 after the final
   application target no longer publishes that socket.
8. Install, verify, enable, start, reload, stop, and restart the safe unit. The
   stop test may stop only server/Caddy; PostgreSQL must remain running and
   unchanged throughout.
9. Prove shared/exclusive contention using actual `roger` and `gha` processes,
   verify refreshed user-manager/runner group membership, and run one complete
   scheduled off-host backup through the canonical shared lock.

## Dry-run evidence

The streamed exact target dry run proposed only:

- recreate/start `utility-watershed-analytics-server-1`; and
- recreate/start `utility-watershed-analytics-caddy-1`.

It named no database action. The original Actions-checkout rollback dry run
reported both application services running and also named no database action.
The exact database digest resolved locally on `wepp3` to the frozen image ID.

## Rollback

Before the safe unit is enabled, application rollback uses the current Actions
checkout, project name `utility-watershed-analytics`, the retained
root-protected legacy runtime values, and:

```text
docker compose up --detach --no-build --no-deps --pull never server caddy
```

This restores the former application/Caddy configuration only. It must be
dry-run first and rejected if a database action appears. If the safe unit has
been installed, disable it without `--now` before leaving the old application
path active. Re-add UFW port 8000 only if the exercised rollback requires the
former direct socket. Never invoke `down`, stop PostgreSQL, change the project,
attach a volume, or install the unsafe checkout unit.

Final accepted state reapplies the interim application target, removes the
obsolete port-8000 firewall allowance, enables the safe unit, and preserves
the exact database invariants above.

Execution clarified that the old Compose rollback requires legacy superuser
placeholders absent from the minimized runtime. The exercised rollback
therefore used the retained legacy environment after it was protected as
root-owned mode `0600`; the accepted target returned to the minimized runtime.

The final safety review also found the connected runner checkout still uses
the old lock-bypassing deployment workflow. Commit/push were excluded, so the
idle runner was stopped and disabled after its group/health proof. It must stay
disabled until the safe workflow is published and verified.
