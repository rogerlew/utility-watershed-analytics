# Database Domain and Identity Audit

Status: DB06 complete with accepted aggregate production evidence

Date: 2026-07-16

This document is the authoritative current-state input to DB07. It describes
what the application and loader do today. It does not choose future
`collection_key`, `watershed_key`, lineage, metadata precedence, or route
migration policy.

## Evidence boundary

The audit combines:

- Static source review of Django models and migrations, loader discovery and
  writers, API routes and serializers, and client routes/API/query consumers;
- Ran tests of the aggregate read-only identity audit against disposable
  PostGIS test databases; and
- Ran aggregate read-only queries against the development database on
  `forest1`; and
- Ran the reviewed aggregate-only audit against `wepp3` under separate
  read-only authority.

The development watershed-domain tables are empty because the configured
external tokens expired before seeding. Development counts therefore prove the
command and schema boundary only. The later production audit observed 126
watersheds, 195,457 subcatchments, and 86,895 channels with zero duplicate
business-key groups/rows and zero child orphans. It selected no row values or
credentials and made no production change.

## Table ownership and lifecycle

The development database contains 55 non-system tables. They divide into four
ownership classes.

### Watershed release domain

These three tables are the only current tables owned by watershed data loading
and future reconciliation:

| Table | Rows on `forest1` | Role | Lifecycle |
| --- | ---: | --- | --- |
| `public.watershed_watershed` | 0 | Watershed boundary, source metadata, and current public run identity | Replaced or reconciled as watershed-domain data |
| `public.watershed_subcatchment` | 0 | Hillslope geometry plus Parquet-enriched attributes | Child of one watershed; cascade-deleted with it |
| `public.watershed_channel` | 0 | Channel geometry and identifiers | Child of one watershed; cascade-deleted with it |

No non-domain foreign key references these tables in the development catalog.
That absence is a required invariant before a release may delete or replace a
watershed.

### Persistent Django application and control state

These ten tables are not watershed release data and must survive reconciliation:

| Table | Rows on `forest1` | Persistence reason |
| --- | ---: | --- |
| `public.auth_group` | 0 | Administrative authorization state |
| `public.auth_group_permissions` | 0 | Administrative authorization state |
| `public.auth_permission` | 52 | Django authorization catalog |
| `public.auth_user` | 1 | Operational Django account |
| `public.auth_user_groups` | 0 | Administrative authorization state |
| `public.auth_user_user_permissions` | 0 | Administrative authorization state |
| `public.django_admin_log` | 0 | Administrative audit history |
| `public.django_content_type` | 13 | Django model identity catalog |
| `public.django_migrations` | 32 | Applied schema history |
| `public.django_session` | 0 | Administrative session state |

The application has no public end-user account workflow, but the database does
contain one development operational account. “No user accounts” must therefore
be interpreted as no product user accounts, not permission to delete Django
auth/admin state.

### Observability state

These five Silk tables are operational telemetry, not watershed data:

| Table | Rows on `forest1` |
| --- | ---: |
| `public.silk_profile` | 0 |
| `public.silk_profile_queries` | 0 |
| `public.silk_request` | 5 |
| `public.silk_response` | 5 |
| `public.silk_sqlquery` | 1 |

Silk retention or disablement belongs to DB04. Reconciliation must not treat
these tables as watershed children.

### PostGIS infrastructure and reference state

These 37 tables are extension-owned and are never watershed release members:

- `public.spatial_ref_sys`: 8,500 rows;
- `topology.layer` and `topology.topology`: 0 rows each;
- non-empty TIGER support tables:
  `direction_lookup` (28), `geocode_settings_default` (7),
  `loader_lookuptables` (13), `loader_platform` (2),
  `loader_variables` (1), `pagc_gaz` (835), `pagc_lex` (2,938),
  `pagc_rules` (4,354), `secondary_unit_lookup` (39),
  `state_lookup` (59), and `street_type_lookup` (609); and
- zero-row TIGER tables: `addr`, `addrfeat`, `bg`, `county`,
  `county_lookup`, `countysub_lookup`, `cousub`, `edges`, `faces`,
  `featnames`, `geocode_settings`, `place`, `place_lookup`, `state`,
  `tabblock`, `tabblock20`, `tract`, `zcta5`, `zip_lookup`,
  `zip_lookup_all`, `zip_lookup_base`, `zip_state`, and `zip_state_loc`.

## Current database and business identities

| Entity | Database primary key | Current business key | Database-enforced | Current source/load key |
| --- | --- | --- | --- | --- |
| Watershed | `runid` | `runid` | Yes, primary key | GeoJSON `properties.runid` or configured standalone `runid` |
| Subcatchment | Surrogate `id` | `(watershed_id, topazid)` | No | Writer merges GeoJSON by `(topazid, weppid)` within one run |
| Channel | Surrogate `id` | `(watershed_id, topazid, weppid, order)` | No | Writer merges GeoJSON by `(topazid, weppid, order)` within one run |

`runid` is a source revision identifier, not a stable project-owned watershed
identity. It is nevertheless the current database primary key and compatibility
key throughout the product.

The subcatchment business key is intentionally narrower than the writer's
GeoJSON grouping key. Current Parquet enrichment looks up exactly one
subcatchment by `(runid, topazid)` and does not include `weppid`. If a source has
two subcatchments with the same `topazid` and different `weppid`, the writer can
create both but Parquet enrichment and the client cannot distinguish them
reliably. DB07 must not silently redefine this key; accepted data must first
prove whether that case exists.

The development catalog has foreign keys from both child tables to
`watershed_watershed.runid`. Django declares `on_delete=CASCADE`, and PostgreSQL
enforces the references. No unique constraint enforces either child business
key. The loader management command also has a global `--force` path that
explicitly deletes channels, subcatchments, and watersheds inside one
transaction. Persistent, observability, and extension tables are outside that
deletion boundary.

## Collection and member identity

There is no collection table or collection column in the current database.
Collection membership exists only in loader configuration and source run IDs:

- batch `nasa-roses-2026-sbs`, whose run IDs use
  `batch;;nasa-roses-2026-sbs;;<member>`;
- batch `victoria-ca-2026-sbs`, whose run IDs use
  `batch;;victoria-ca-2026-sbs;;<member>`;
- standalone Gate Creek, configured as `aversive-forestry`; and
- standalone Mill Creek, configured as `mdobre-invincible-scarab`.

Batch membership is selected with a substring containing the configured batch
URL's final path segment. NASA ROSES member suffixes are uppercased during
normalization; other batch suffixes and standalone IDs preserve case.
Standalone display names are metadata, not identity.

Fields such as `pws_id`, `huc10_id`, utility names, and geometry are nullable or
can be shared across logical watersheds. They are descriptive/source metadata,
not current database keys. The same HUC10 geometry may represent multiple
utilities, and a logical watershed can move between source batches or receive a
new upstream run ID.

## Parquet and analytical joins

The server loader enriches subcatchments per `runid` from three Parquet classes:

| Artifact | Accepted join-column spellings | Database target | Required uniqueness |
| --- | --- | --- | --- |
| `watershed/hillslopes.parquet` | `TopazID`, `topaz_id`, `topazid`, `TOPAZID`, `Topaz_ID`, `topaz_ID` | `Subcatchment.topazid` | At most one row per `topazid` within the run |
| `soils/soils.parquet` | Same | `Subcatchment.topazid` | At most one row per `topazid` within the run |
| `landuse/landuse.parquet` | Same | `Subcatchment.topazid` | At most one row per `topazid` within the run/scenario |

The loader currently calls `set_index(topaz_column)` and then `loc[topazid]`.
It does not reject duplicate index values before mapping fields. Duplicate
Parquet identities can therefore return a DataFrame where one row is expected
and produce ambiguous or failing enrichment. DB08 schemas must reject them;
DB07 must keep the join key explicit.

Client-side query-engine consumers add more current compatibility keys:

- land-use lookup maps one result per `topaz_id` and overwrites earlier rows
  with the same key;
- RAP hillslope and choropleth queries filter or join on `topaz_id`;
- WEPP scenario loss rows use `wepp_id` for hillslope metrics; and
- all query-engine dataset paths are scoped by `runId`.

No artifact checksum, schema version, source revision, or join-contract version
is persisted with the three database tables today.

## API and client compatibility surface

Changing `runid` currently affects all of the following:

- `Watershed.runid`, the database primary key and both child foreign keys;
- watershed GeoJSON `feature.id`;
- DRF watershed detail, subcatchment, channel, SBS, RHESSys spatial, and RHESSys
  output URL path segments;
- client route `/watershed/$webcloudRunId` and `useRunId()`;
- React Query keys for subcatchments, channels, land use, scenarios, SBS,
  RAP, and RHESSys products;
- direct WEPPcloud dashboard, report, raster, and query-engine paths; and
- server/client in-memory discovery, geometry, and tile caches.

Subcatchment and channel GeoJSON `feature.id` values are surrogate database IDs,
so they can change after a reload. The API exposes `topazid` and `weppid` as
properties. The map uses the surrogate feature ID only for transient layer
selection and uses `topazid` for hillslope selection and analytical joins.
Bookmarks and durable references must not adopt the surrogate child IDs.

Static review also found schema-description drift that DB07/DB08 must account
for rather than mistake for identity:

- `WatershedProperties` declares several fields that the current list endpoint
  does not include, including `pws_id`, while search falls back to `pws_id` only
  when `feature.id` is absent;
- `SubcatchmentProperties` includes `watershed` and fields not emitted by the
  endpoint's explicit property list; and
- the client type still declares removed field `ll`.

These mismatches do not change the current key, but versioned schemas must make
the actual response contract explicit.

## Schema-signature inputs

DB09 will define canonical fingerprints. DB06 establishes the current inputs
that must be represented rather than relying on table names alone:

1. applied watershed migrations `0001` through `0006`;
2. table and column names, database field types, nullability, primary-key and
   unique flags;
3. geometry type and SRID for every domain geometry column;
4. exact current and proposed business-key column sequences;
5. foreign-key columns, targets, database enforcement, and Django deletion
   behavior;
6. loader field-source maps and accepted Topaz column spellings;
7. Parquet authoritative-field maps and join-contract version;
8. public route, GeoJSON ID/property, and client cache-key compatibility; and
9. PostGIS extension/image compatibility and applied migration state.

Database surrogate child IDs, sequence values, row order, timestamps, and
environment-specific database/container names are not logical schema-signature
inputs.

## Executable read-only audit

Run the deterministic aggregate audit in an application container connected to
the database being assessed:

```bash
python manage.py audit_domain_identity --fail-on-violations
```

The command:

- starts a transaction and sets it read-only before inspection;
- reports counts, field signatures, applied watershed migrations, key
  enforcement, duplicate-group counts, foreign-key enforcement, cascade
  behavior, and orphan counts;
- emits no row keys, values, database credentials, hostnames, or database user;
- exits non-zero for duplicate current business keys or orphan children; and
- warns when child keys lack database constraints or all domain tables are
  empty.

On `forest1`, the command passed with zero rows and zero duplicate/orphan groups,
while correctly warning that child keys are not database-enforced and empty
tables cannot establish clean production data. Tests prove the command detects
duplicate subcatchment and channel keys and issues no DDL or data-mutation query.
On `wepp3`, the same reviewed implementation passed against non-empty data with
zero duplicate groups and zero orphans. Child business keys remain unconstrained.

## DB07 inputs and blockers

DB07 must resolve these questions using accepted data evidence:

1. assign stable project-controlled watershed and collection keys independently
   of source `runid`;
2. define source-revision aliases and redirect duration for current public URLs;
3. decide how batch moves, source replacement, split/merge, and multiple
   utilities sharing one geometry affect logical identity;
4. confirm `(watershed, topazid)` for subcatchments and
   `(watershed, topazid, weppid, order)` for channels against a non-empty current
   dataset before DB migrations add constraints;
5. define whether child GeoJSON receives a stable explicit identity or exposes
   only run-scoped business properties; and
6. reconcile actual API response schemas with client types.

The accepted production evidence is preserved in the DB06 work package. It
supports the current-data observations above, not a promise that future loads
remain clean. DB07 must still define stable identity and metadata authority;
later schema work must add constraints only after that contract is accepted.
