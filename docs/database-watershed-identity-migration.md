# Stable Watershed Identity Migration

Status: DB13 additive schema accepted

Date: 2026-07-17

This document defines the database and API compatibility shape implemented by
DB13. It applies the accepted DB07 identity rules without assigning unreviewed
batch-member keys or changing production.

## Relational shape

DB13 adds three identity tables while retaining the existing serving tables:

| Model | Identity | Purpose |
| --- | --- | --- |
| `WatershedCollection` | project-controlled `key` | Stable source grouping across batch or standalone revisions. |
| `WatershedIdentity` | generated UUID plus nullable unique `watershed_key` | Immutable internal row and reviewed public logical key. |
| `WatershedRunAlias` | permanent unique `runid` | Maps every current or retained historical source revision to one logical watershed. |

The generated UUID is database-internal and is not serialized, routed, or
included in release fingerprints. The project-controlled `watershed_key` is the
durable public identity. It remains nullable only during expansion because the
DB07 contract deliberately forbids inferred batch-member assignments.

`Watershed.logical_watershed` is a nullable one-to-one link to the current
serving row. `Subcatchment.logical_watershed` and
`Channel.logical_watershed` are nullable dual links. Their existing
`watershed_id` foreign keys remain intact for old code during the compatibility
window.

One partial unique constraint permits at most one current run alias per logical
watershed. The run alias primary key prevents one run ID from resolving to two
logical watersheds. Alias activation refuses to move an existing alias to a
different identity.

## Backfill rules

Migration `watershed.0007_stable_watershed_identity` creates one internal
identity and one current run alias for every existing `Watershed`, then links
all existing children without changing their primary keys.

Only exact DB07 assignments are applied automatically:

| Source run | Collection key | Watershed key |
| --- | --- | --- |
| `aversive-forestry` | `gate-creek` | `gate-creek` |
| `mdobre-invincible-scarab` | `mill-creek` | `mill-creek` |
| `some-oligopoly` | `mill-creek` | `mill-creek` |
| `batch;;nasa-roses-2026-sbs;;*` | `nasa-roses` | unassigned |
| `batch;;nasa-roses-202606-psbs;;*` | `nasa-roses` | unassigned |
| `batch;;victoria-ca-2026-sbs;;*` | `victoria-ca` | unassigned |

The asterisk above describes collection recognition only; the migration never
derives a watershed key from the member suffix. Unknown collections and
watershed keys remain null. If both accepted Mill Creek revisions appear as
simultaneously current source rows, migration fails rather than guessing which
row is serving.

## Compatibility points

1. **Old schema and old code:** existing behavior before migration.
2. **Expanded schema and old code:** old model state can read the expanded
   tables because every new serving-table column is nullable and every old
   column and foreign key remains unchanged. The legacy destructive loader
   remains prohibited in production.
3. **Expanded schema and DB13 code:** current run IDs resolve through permanent
   aliases with a direct-row fallback for an old-code insert. New child writes
   copy the parent's logical link. The validation command rejects incomplete or
   mismatched links before a later contract step.
4. **Reviewed key assignment:** release preparation or baseline adoption binds
   every remaining identity to its reviewed `watershed_key`; it may not infer
   assignments from labels, HUCs, geometry, or matching source suffixes.
5. **Later contract:** only after the dual-compatible rollout and complete key
   assignment may a successor migration make logical links non-null and remove
   the old revision-scoped child links. DB13 does not perform that contraction.

Source replacement activates a new alias on the same identity. During the
compatibility window, `Watershed.runid` remains the legacy row anchor rather
than being updated or delete/reinserted. The watershed row, child rows, child
database IDs, and stable feature IDs therefore survive replacement unchanged.

## API behavior

DB13 adds:

- `/api/watershed/by-key/<watershed_key>/`;
- `/api/watershed/by-key/<watershed_key>/subcatchments`; and
- `/api/watershed/by-key/<watershed_key>/channels`.

The stable-key watershed feature ID is the `watershed_key`. Stable child feature
IDs follow DB07 exactly:

- `subcatchment:<watershed_key>:<topazid>`; and
- `channel:<watershed_key>:<topazid>:<weppid>:<order>`.

Existing run-ID routes remain read-only aliases and retain their legacy response
ID shapes. Both the current run and retained historical run IDs resolve to the
same serving rows. A retired known identity returns 410; a never-known stable
key or watershed detail run ID returns 404. The existing legacy behavior of an
empty 200 for an unknown child-list run ID is preserved during compatibility.

The detail responses also carry `watershed_key` and `current_runid`. When the
stable key is assigned, `/watershed/<runid>` redirects in the client to
`/watershed/key/<watershed_key>`. The canonical route retains the resolved
`current_runid` in a narrow route context so existing analytics, query-engine,
SBS, RHESSys, and external WEPPcloud calls continue using the source revision.
An unassigned legacy route does not redirect.

Stable-key SBS/RHESSys API paths remain deferred until their materialized
capability dependencies are implemented; the browser compatibility bridge does
not send a stable key to a source-run endpoint.

## Validation and rollback

Run after migration and before accepting the expanded state:

```bash
python manage.py validate_watershed_identity --fail-on-violations
```

The aggregate-only command checks complete watershed and child links, parent/
child identity agreement, one serving row and current alias per active identity,
and no current alias on a retired identity. Nullable unreviewed
`watershed_key` values are counted but are not an expansion violation.

The migration is reversible only before identity-aware writes. Its reverse path
requires exactly one identity and matching current alias for every linked legacy
watershed. Once a new alias or other stable-identity record is written, reverse
migration fails closed with a roll-forward instruction. Recovery beyond that
boundary is restore of the additive schema followed by roll-forward, never
silent deletion of identity history.

The DB13 forest1 rehearsal used the accepted DB06 aggregate shape: 126
watersheds, 195,457 subcatchments, and 86,895 channels. Forward migration took
15.268 seconds and pre-write rollback took 12.631 seconds in disposable PostGIS;
counts and sampled minimum/maximum child IDs were unchanged. This is isolated
rehearsal evidence, not a production lock-duration claim.
