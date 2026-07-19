# Self-hosted artifact serving

Status: DB30B installed, active, and independently verified on 2026-07-19

This runbook owns the public delivery path for immutable production artifacts.
The storage is operator-owned infrastructure; no external storage or CDN
provider is part of the design.

## Architecture

```text
public client
  -> https://firewisewatersheds.org/artifacts/v1/production/...
  -> wepp3 Caddy on public ports 80/443
  -> http://100.87.36.38:18080 over Tailscale
  -> forest1 read-only Caddy origin
  -> /wc1/utility-watershed-analytics-artifacts/v1/production
```

- `wepp3` has Tailscale address `100.74.181.119`.
- `forest1` has Tailscale address `100.87.36.38`.
- The origin binds only `100.87.36.38:18080` and permits only the two stated
  Tailscale addresses. It does not bind the forest1 LAN address.
- The production proxy matches only host `firewisewatersheds.org` and path
  `/artifacts/v1/production/*`. All other traffic follows the existing API and
  frontend route.
- Objects are content-addressed and mounted read-only. Rollback never deletes
  or modifies the `/wc1` namespace.

## Forest1 origin

The origin is a rootless user service for `roger`:

- unit: `~/.config/systemd/user/uwa-artifact-origin.service`;
- generated config: `~/.config/utility-watershed-analytics/artifact-origin.Caddyfile`;
- repository unit template: `ops/systemd/uwa-artifact-origin.service`;
- repository generator: `scripts/generate_artifact_origin_caddy.py`;
- container: `uwa-artifact-origin` using the reviewed Caddy image;
- persistence: the user service is enabled and `loginctl` linger is enabled.

The generator reads the exact release manifest, verifies its reviewed SHA-256,
discovers every declared artifact, checks each local size, and emits explicit
paths with the reviewed media types. The installed DB30B configuration exposes
996 referenced objects plus the manifest: 393 Parquet, 371 GeoJSON, 129 JSON,
and 103 TIFF files.

Check the origin without exposing it elsewhere:

```bash
systemctl --user status uwa-artifact-origin.service
systemctl --user is-enabled uwa-artifact-origin.service
ss -ltn '( sport = :18080 )'
curl --fail --silent --show-error \
  http://100.87.36.38:18080/v1/production/objects/sha256/bb/\
bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5 \
  -o /dev/null
```

## Production proxy

DB30B installs protected runtime material outside the checkout so a normal
checkout change cannot silently remove the route:

- `/etc/utility-watershed-analytics/artifact-proxy.Caddyfile`, mode `0600`;
- `/etc/utility-watershed-analytics/compose.artifact-proxy.yml`, mode `0600`;
- `/usr/local/lib/utility-watershed-analytics-artifact-serving/`, mode `0700`;
- `/etc/systemd/system/utility-watershed-analytics.service.d/30-db30b-artifact-route.conf`.

The Compose override mounts the protected Caddyfile read-only. The systemd
drop-in invokes `ensure_artifact_proxy.sh` after start and instead of the base
reload action. That helper validates the protected override by checksum,
renders Compose, updates only `server` and `caddy` with `--no-deps`, applies
the route, and asserts the exact read-only mount. Both paths use the canonical
exclusive operations lock.

Check the installed route on wepp3:

```bash
sudo systemctl status utility-watershed-analytics.service
sudo systemctl reload utility-watershed-analytics.service
sudo systemd-analyze verify utility-watershed-analytics.service
docker inspect utility-watershed-analytics-caddy-1 \
  --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}} rw={{.RW}}{{end}}{{end}}'
```

## Public verification

For each release, verify the manifest and at least one TIFF and Parquet object
from a host other than wepp3. Compare the complete byte count and SHA-256 with
the reviewed manifest. Also verify `Content-Type`, `Accept-Ranges: bytes`, and
a bounded Parquet range request returning `206` and the requested byte count.
Then exercise one real materialized API query and each declared capability.

DB30B's accepted manifest is
`bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5`.
Its public manifest, representative TIFF and Parquet objects, Gate Creek query,
and Sooke09/Sooke15 catalog and tile reads passed after both a canonical
systemd reload and a bounded Caddy container restart.

## Publishing a new manifest

Do not edit the generated Caddyfile by hand.

1. Complete the governed release package and place only its immutable,
   checksum-addressed bytes below the existing forest1 production namespace.
2. Run `scripts/generate_artifact_origin_caddy.py` with the new manifest path,
   exact reviewed manifest SHA-256, existing artifact root/listener, both
   allowed Tailscale IPs, and a protected temporary output.
3. Validate the generated configuration with the pinned Caddy image and verify
   every referenced local file before replacing the installed origin config.
4. Restart only `uwa-artifact-origin.service` and perform exact origin reads.
5. Perform independent public object, range, API, and capability checks before
   activating the corresponding database release.
6. Record hashes, image identity, results, and cleanup in the authorized work
   package and ignored administrative log.

## Recovery

If a database release is `ACTIVE`, run that release package's exact rehearsed
database rollback first and prove coherent fallback. Only then restore the
previous protected production Caddy configuration and stop or disable the
forest1 origin if the route itself must be withdrawn. Verify ordinary API and
frontend behavior after each step.

Never delete, mutate, or relocate
`/wc1/utility-watershed-analytics-artifacts/v1/production` as rollback. Never
introduce a provider as an operational shortcut. Preserve the encrypted backup,
manifest, adoption plan, persistence plan, and sanitized evidence needed to
reproduce the accepted state.
