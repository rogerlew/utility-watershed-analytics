# Production Database and Data-Source Inventory

This document is the authoritative inventory of watershed datasets intended
for the production Utility Watershed Analytics deployment. It records both the
observed production state and the approved target state so an incomplete data
migration is not mistaken for the desired configuration.

The proposed representation and deployment process for this inventory is
specified in
[Database Deployment Architecture and Tooling](database-deployment-architecture.md).
Implementation order and bounded execution records are maintained in the
[forward roadmap](ROADMAP.md) and
[work-package catalog](work-packages/README.md).

Last updated: 2026-07-16

## Scope and authority

The PostgreSQL/PostGIS database stores watershed, subcatchment, channel, soil,
land-use, and related attributes loaded by the Django watershed loader.
RHESSys rasters, GeoJSON, and Parquet outputs are not stored in PostgreSQL;
the current application reads or proxies them from the corresponding WEPPcloud
run. The approved deployment target requires accepted RHESSys assets to be
copied into project-controlled, no-TTL storage and exposed through materialized
capability configuration. Consequently, a watershed row in PostgreSQL does not
prove that its RHESSys assets are available or release-ready.

Update this document in the same pull request as any change to an accepted
batch, standalone run ID, master GeoJSON, or RHESSys asset location. After a
production data operation, update the observed snapshot and verification date.
Run IDs in this document are case-sensitive.

Lifecycle terms:

- **Retain**: accepted and expected to remain in production.
- **Add**: accepted but not yet present in the verified production snapshot.
- **Replace**: accepted successor to a dataset that will be retired.
- **Retire**: may still be present temporarily, but is not part of the target
  inventory.

## Approved inventory

| Dataset | Canonical run ID or prefix | Lifecycle | Production database | RHESSys assets | Required action |
| --- | --- | --- | --- | --- | --- |
| Gate Creek | `aversive-forestry` | Retain | Present | Observed in WEPPcloud: spatial inputs plus dynamic scenario Parquets for `S1`, `S2`, and `S4b` | Retain the database row; copy, index, and verify the RHESSys assets in durable project storage. |
| Mill Creek | `some-oligopoly` | Replace | Not present as of 2026-07-16 | Must be re-vendored to durable project storage | Configure and load the new standalone run, publish the required RHESSys assets durably, verify them, and then retire the former run. |
| Former Mill Creek | `mdobre-invincible-scarab` | Retire | Present as of 2026-07-16 | Unavailable; the run is believed to have been removed by the deletion TTL | Remove from the database only after `some-oligopoly` is loaded and validated. Do not treat this run as a recoverable source. |
| Victoria, BC | `batch;;victoria-ca-2026-sbs;;<member>` | Retain | Present; 31 members | WEPPcloud output maps are confirmed for `Sooke09` and `Sooke15` only | Retain the batch; copy and verify those assets in durable project storage. Do not infer RHESSys availability for other members. |
| NASA ROSES, current | `batch;;nasa-roses-2026-sbs;;<member>` | Retire | Present; 93 members | None recorded | Replace with the 202606 PSBS batch after enrichment and load validation. |
| NASA ROSES, successor | `batch;;nasa-roses-202606-psbs;;<member>` | Replace | Not present as of 2026-07-16 | None recorded | Enrich its resources GeoJSON as specified below, configure the loader, load it, validate it, and then retire the old NASA batch. |
| Bremerton | `batch;;bremerton-2026-psbs;;<member>` | Add | Not present as of 2026-07-16 | None recorded | Add the batch to loader configuration and load it after validating its resources GeoJSON and per-run products. |

The full Victoria batch identifier is
`batch;;victoria-ca-2026-sbs;;<member>`. Shortened forms such as
`batch;;victoria-ca-2026` are descriptive only and must not be stored as run
IDs.

## Stable identity assignments

DB07 assigns project-controlled collection keys independently of replaceable
source revisions:

- Gate Creek: collection and watershed key `gate-creek`;
- Mill Creek: collection and watershed key `mill-creek` for both the current
  and successor run;
- NASA ROSES: collection key `nasa-roses`; and
- Victoria: collection key `victoria-ca`.

Batch watershed keys use reviewed member-index mappings. A normalized source
suffix may propose a key such as `victoria-ca-sooke09`, but suffix, name, HUC,
utility, or geometry similarity never assigns identity automatically. The full
naming, replacement, move, split/merge, route-alias, retirement, and field
authority rules are in the
[database identity and metadata authority contract](database-identity-metadata-contract.md).

## RHESSys inventory

RHESSys capability is associated with the external run, not a database column.
The authoritative RHESSys-enabled run list is therefore:

| Run ID | Watershed | Supported product form | Status verified 2026-07-16 |
| --- | --- | --- | --- |
| `aversive-forestry` | Gate Creek | Spatial-input GeoTIFFs; scenario, basin, hillslope, and patch Parquets used for dynamic maps and time series | Observed available in WEPPcloud. Durable copy and capability activation remain pending. The precomputed `rhessys/maps/` directory is not required. |
| `some-oligopoly` | Mill Creek | Precomputed RHESSys output GeoTIFFs under `rhessys/maps/` | Pending durable re-vendoring and verification. |
| `batch;;victoria-ca-2026-sbs;;Sooke09` | Sooke09 | Precomputed RHESSys output GeoTIFFs under `rhessys/maps/` | Observed available in WEPPcloud, including baseline, fire/thinning change, and one-year difference products. Durable copy remains pending. |
| `batch;;victoria-ca-2026-sbs;;Sooke15` | Sooke15 | Precomputed RHESSys output GeoTIFFs under `rhessys/maps/` | Observed available in WEPPcloud, including baseline and fire/thinning change products. Durable copy remains pending. |

No other production run should be described as RHESSys-enabled without adding
it to this table after its required external assets have been verified.
No declared capability is ready for release activation until its immutable
asset index and project-controlled durable copy have also been verified.

### Mill Creek re-vendoring acceptance criteria

Before switching the application from `mdobre-invincible-scarab` to
`some-oligopoly`:

1. Establish and record the new run's actual project directory (for example,
   `disturbed9002` versus `disturbed9002_wbt`) in the standalone loader
   configuration.
2. Load and validate its boundary, subcatchments, channels, hillslope, soil,
   and land-use products.
3. Publish the precomputed RHESSys map scenario directories and registered
   GeoTIFF variables expected by the application under `rhessys/maps/` in
   project-controlled, no-TTL storage with an immutable asset index.
4. Verify the RHESSys catalog endpoint returns at least one scenario and that a
   tile from every published variable can be rendered.
5. Update application references and development run lists from
   `mdobre-invincible-scarab` to `some-oligopoly`.
6. Remove the former database row only after the new watershed and RHESSys
   views pass validation.

## NASA 202606 resources enrichment contract

The target master resource is the resources GeoJSON belonging to
`batch;;nasa-roses-202606-psbs`. Its target run IDs and geometries must remain
authoritative. Enrich it with watershed attributes from:

<https://bucket.bearhive.duckdns.org/WWS_Watersheds_HUC10_Merged.geojson>

Source observed on 2026-07-16:

- 395 GeoJSON features
- 8,935,440 bytes
- `Last-Modified: Wed, 10 Dec 2025 17:39:31 GMT`
- SHA-256:
  `be152890a8436d931f962b6eabe32287935d8da5303c5f532985ec835e8954ce`
- `WWS_Code` is present and unique across all 395 features.
- `PWS_ID` is present but is not unique: there are 283 distinct values, so it
  is not a safe join key by itself.

Copy these source properties when matches are established:

- `PWS_ID`
- `SrcName`
- `PWS_Name`
- `County_Nam`
- `State`
- `HUC10_ID`
- `HUC10_Name`
- `WWS_Code`
- `SrcType`
- `Shape_Leng`
- `Shape_Area`
- `outlet_lon_lat`

Do not copy the source `runid`: the enrichment file contains historical
`batch;;nasa-roses-2025;;<member>` identifiers. Do not replace the target
geometry. `WWS_Code` is the candidate join key, but the merge must first prove
that it is present and unique in the target resource. Produce an unmatched and
duplicate-key report rather than silently dropping or multiplying features.

The enrichment source does **not** contain the current Django utility metadata
properties `OwnerType`, `PopGroup`, `TreatType`, `ConnGroup`, or the
`HUC10_*` utility aggregates. If those fields must remain populated in the
successor batch, they require a separate, identified source. Also note that
`outlet_lon_lat` is not currently represented by a Django model field and will
remain only in the GeoJSON unless the database schema is extended.

The enriched resource is accepted only when:

1. its feature count and geometry values match the unmodified target resource;
2. every feature has a non-null, unique `runid` beginning with
   `batch;;nasa-roses-202606-psbs;;`;
3. join-key uniqueness, matched, unmatched, and duplicate counts are recorded;
4. no historical source `runid` has been copied into the output;
5. `data_release validate` and an isolated staging build preserve the expected
   watershed, subcatchment, and channel relationships; the current loader's
   `--dry-run` output is not sufficient validation; and
6. the observed production snapshot below is updated after the final load.

DB18 implements and synthetically proves the fixed transformation and immutable
provenance mechanics in the
[NASA enrichment contract](database-nasa-202606-enrichment-contract.md). It did
not fetch either real input or update this observed snapshot. DB30 remains the
owner of real locked membership and artifacts.

## Observed production snapshot

Read-only inspection of `wepp3` on 2026-07-16 found:

| Stored source | Watersheds | `owner_type` populated | `huc10_utility_count` populated |
| --- | ---: | ---: | ---: |
| `nasa-roses-2026-sbs` | 93 | 85 | 92 |
| `victoria-ca-2026-sbs` | 31 | 0 | 0 |
| `aversive-forestry` | 1 | 0 | 0 |
| `mdobre-invincible-scarab` | 1 | 0 | 0 |
| **Total** | **126** | **85** | **92** |

Associated-table totals were 195,457 subcatchments and 86,895 channels. This
snapshot describes what is stored, not the approved target inventory. In
particular, the old NASA and Mill Creek records remain present while their
successors are pending.

Use this read-only query to refresh the grouped snapshot:

```sql
SELECT
    CASE
        WHEN runid LIKE 'batch;;%'
            THEN split_part(runid, ';;', 2)
        ELSE 'standalone:' || runid
    END AS source,
    count(*) AS watersheds,
    count(owner_type) AS owner_type_present,
    count(huc10_utility_count) AS huc10_aggregates_present
FROM watershed_watershed
GROUP BY 1
ORDER BY 1;
```

## Loader and database boundaries

The observed production inventory is currently loaded through the batch and
standalone configuration in `server/server/watershed/loaders/config.py`. The
approved target inventory above is not yet fully represented there: the NASA
successor, new Mill Creek run, and Bremerton batch remain pending. The current
loader materializes three geometry-bearing tables:

- `watershed_watershed`: one row per canonical run ID;
- `watershed_subcatchment`: subcatchments linked to a watershed by foreign key;
- `watershed_channel`: channels linked to a watershed by foreign key.

RHESSys discovery currently probes WEPPcloud on demand and caches discovery
results in application memory for one hour. It does not persist availability
in PostgreSQL. A database backup therefore protects the loaded watershed
tables but does not protect the external RHESSys assets or master GeoJSON
resources; those must be retained separately.
