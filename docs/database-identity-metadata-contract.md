# Database Identity and Metadata Authority Contract

Status: DB07 version 1 accepted

Date: 2026-07-17

This document is the authoritative input to DB08 for logical identity,
lineage, route compatibility, child business keys, and watershed metadata and
geometry authority. DB08 may encode these decisions in schemas; it must not
silently choose different identities or precedence.

## 1. Contract boundary

Version 1 decides:

- immutable project-controlled collection and watershed keys;
- replaceable source run revisions and permanent compatibility aliases;
- current child business identities and stable serialized child IDs;
- retained, renamed, replaced, moved, split, merged, and removed lineage;
- legacy run-ID and future stable-key route behavior; and
- field-level authority, null, and conflict rules for the four current source
  collections.

It does not assign all batch members, implement database fields or routes,
define DB08 release schemas, or activate data. Exact batch assignments require
a reviewed member index; keys are not inferred during deployment.

## 2. Key rules

Both `collection_key` and `watershed_key`:

- match `^[a-z0-9]+(?:-[a-z0-9]+)*$`;
- contain 1–96 ASCII characters;
- are assigned by this project, not copied from a source run ID;
- are opaque after assignment: spelling does not change when names, ownership,
  geometry, collection membership, or source revisions change;
- are globally unique within their key type; and
- are tombstoned permanently after retirement and never reused.

Normalization may propose a new key by lowercasing an ASCII label, replacing
non-alphanumeric runs with one hyphen, and trimming hyphens. That proposal is
not identity evidence. A reviewed mapping must confirm that a source member is
new, retained, replaced, split, merged, or moved before the key is accepted.

### 2.1 Initial collection assignments

Collection keys describe logical project groupings and do not include mutable
source batch dates or run IDs.

| Collection key | Current source revision | Known successor revision | Decision |
| --- | --- | --- | --- |
| `gate-creek` | standalone `aversive-forestry` | none accepted | Stable standalone grouping. |
| `mill-creek` | standalone `mdobre-invincible-scarab` | `some-oligopoly` | One collection across the source replacement. |
| `nasa-roses` | batch `nasa-roses-2026-sbs` | `nasa-roses-202606-psbs` | One collection across the reviewed batch replacement. |
| `victoria-ca` | batch `victoria-ca-2026-sbs` | none accepted | Stable Victoria grouping. |

`bremerton` is the reserved collection-key candidate for the approved future
batch. DB08 may encode it only after its first reviewed member index confirms
the assignment.

### 2.2 Initial watershed assignments

- Gate Creek: `watershed_key = gate-creek`.
- Mill Creek: `watershed_key = mill-creek` for both the current and successor
  source run revisions.
- Batch-member candidate keys use
  `<collection_key>-<normalized-member-label>`, for example
  `victoria-ca-sooke09` and `nasa-roses-or-20`.

Batch normalization is only a candidate generator. Matching suffixes across
old and successor batches do not by themselves prove retained identity. The
reviewed member index must bind every source revision to one watershed key and
must reject duplicate candidates or ambiguous matches.

Two utilities may share one HUC10 or identical geometry and still receive
different watershed keys. `pws_id`, `huc10_id`, name, owner, and geometry are
descriptive data, never fallback identity.

## 3. Identity layers

| Layer | Version-1 identity | Change behavior |
| --- | --- | --- |
| Collection | `collection_key` | Stable across source batch/run revisions; changes only when a reviewed collection move occurs. |
| Logical watershed | `watershed_key` | Stable across rename, metadata, geometry, collection move, and source replacement. |
| Source revision | `runid` plus exact source/artifact reference | Replaceable; one active revision per watershed in one release. |
| Subcatchment | `(watershed_key, topazid)` | Retained rows keep logical identity; duplicates fail preparation. |
| Channel | `(watershed_key, topazid, weppid, order)` | Retained rows keep logical identity; duplicates fail preparation. |

The accepted DB06 production audit found zero duplicate groups and zero child
orphans for these child keys. DB14 owns database enforcement. A future source
that cannot satisfy the keys requires a new contract version, not a fallback.

Database surrogate child IDs are not durable identity. The canonical serialized
IDs are:

- `subcatchment:<watershed_key>:<topazid>`; and
- `channel:<watershed_key>:<topazid>:<weppid>:<order>`.

These become GeoJSON feature IDs when the compatible API rollout implements
stable keys. Existing numeric feature IDs remain temporary compatibility data
until then and must not be stored in manifests, bookmarks, or lineage.

## 4. Lineage decisions

Every change is classified before preparation:

| Change | Watershed key behavior | Required lineage |
| --- | --- | --- |
| Retained | Same key | Record the new release membership. |
| Renamed | Same key | Record old/new display metadata; no identity edge. |
| Source replacement | Same key | Record old and new run revisions; old run ID becomes an alias. |
| Collection move | Same key | Record old and new collection keys plus reviewed mapping. |
| Split | New key for every successor | One predecessor-to-many successors; tombstone predecessor. |
| Merge | New key for the successor | Many predecessors-to-one successor; tombstone every predecessor. |
| Deliberate removal | No successor | Tombstone removed key and record the reviewed expected removal. |

Lineage is an acyclic directed graph. Split and merge successors never reuse a
predecessor key because doing so would make old bookmarks and foreign keys
ambiguous. A source rename alone is not split or merge evidence. Preparation
fails when membership, geometry, names, or source IDs suggest more than one
classification and no reviewed mapping resolves it.

## 5. Route compatibility and aliases

Current public and API routes use `runid`. The compatible migration target is:

- canonical browser route: `/watershed/key/<watershed_key>`;
- canonical API root: `/api/watershed/by-key/<watershed_key>/`; and
- the same suffixes for subcatchments, channels, SBS, and RHESSys products as
  the current run-ID routes.

Later route implementation must:

1. resolve an active run ID and every retained historical run-ID alias to one
   watershed key;
2. redirect browser run-ID routes to the canonical stable-key route;
3. keep API run-ID routes as read-only aliases returning the same logical
   watershed during the compatibility period;
4. reject activation when one run ID would resolve to multiple watershed keys;
5. return `410 Gone` for a deliberately retired watershed without a successor;
   and
6. return `404 Not Found` only for identifiers that were never known.

Aliases do not expire on a clock. They remain while any retained release,
rollback release, inventory record, or public compatibility record references
them. Alias garbage collection therefore requires a later reviewed retention
decision, not ordinary release preparation.

## 6. Presence, null, and conflict semantics

Every prepared watershed record contains every version-1 field. A value may be
null only when its matrix cell allows null or requires explicit null.

Authority codes used below:

| Code | Meaning |
| --- | --- |
| `IDX!` | Required from the reviewed member index or standalone source declaration. |
| `MAN!` | Required from project manifest metadata. |
| `BND!` | Required from the locked boundary/master artifact. |
| `META?` | Field must be present in the locked prepared metadata artifact; value may be explicit null. |
| `NULL!` | Must be present as explicit null; a non-null value requires a new contract decision. |
| `DER!` | Deterministically derived from another accepted authoritative field. |

Absent and null are different:

- absent authoritative field: preparation error;
- explicit null in `META?` or `NULL!`: clear the serving value;
- null in an `!` non-null cell: preparation error; and
- stale serving value with authoritative null: update to null.

One field has one final authority. If another source supplies a different
non-null value, preparation fails with both provenance references. Equal values
may pass but do not change authority. The NASA metadata enrichment may contain
historical `runid` and geometry; those two fields are explicitly ignored,
compared, and reported because `IDX!` and `BND!` remain authoritative.

## 7. Current collection authority matrix

The matrix covers every field on the current `Watershed` model. For NASA,
`META?` means the deterministic prepared metadata artifact: current accepted
metadata or the reviewed successor enrichment output with field provenance.
NASA utility fields remain required-presence nullable fields; a successor
cannot silently drop them because the first enrichment source lacks them.

| Model field | `nasa-roses` | `victoria-ca` | `gate-creek` | `mill-creek` |
| --- | --- | --- | --- | --- |
| `pws_id` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `srcname` | `META?` | `BND!` | `MAN!` | `MAN!` |
| `pws_name` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `county_nam` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `state` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `huc10_id` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `huc10_name` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `wws_code` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `srctype` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `shape_leng` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `shape_area` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `area_km2` | `NULL!` | `BND!` | `NULL!` | `NULL!` |
| `owner_type` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `pop_group` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `treat_type` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `conn_group` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `huc10_pws_names` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `huc10_owner_types` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `huc10_pop_groups` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `huc10_treat_types` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `huc10_utility_count` | `META?` | `NULL!` | `NULL!` | `NULL!` |
| `runid` | `IDX!` | `IDX!` | `IDX!` | `IDX!` |
| `geom` | `BND!` | `BND!` | `BND!` | `BND!` |
| `simplified_geom` | `DER!` | `DER!` | `DER!` | `DER!` |

`simplified_geom` is derived only from canonical `geom` with the versioned
materializer settings. It is never copied from a source. `outlet_lon_lat` is
not a current model field; DB08 may carry it as artifact metadata but may not
silently map it into a serving field.

## 8. Independent change channels

- Metadata-only: keys, collection, run revision, geometry fingerprint, and
  child fingerprint stay fixed; the metadata fingerprint changes.
- Geometry-only: keys, collection, run revision, metadata fingerprint, and
  child fingerprint stay fixed; geometry and derived simplified geometry
  change.
- Child-only: watershed keys, metadata, and watershed geometry stay fixed; one
  or more child/artifact fingerprints change and rows reconcile by child key.
- Source replacement: the run revision changes and may carry metadata,
  geometry, and child changes, but the watershed key stays fixed only with a
  reviewed mapping.

A change that crosses more than one channel must declare every changed
fingerprint. Preparation never infers “metadata-only” or “geometry-only” from a
partial artifact.

## 9. Conflict rules

Preparation rejects:

- duplicate collection or watershed keys;
- duplicate normalized key candidates without an explicit assignment;
- one active run ID mapped to multiple watershed keys;
- one watershed key with multiple active run revisions in one release;
- reuse of a tombstoned key;
- source suffix or geometry similarity used as the only retained-identity proof;
- a missing field, unauthorized non-null field, disallowed null, or conflicting
  value/provenance;
- incomplete, cyclic, or key-reusing split/merge lineage; and
- duplicate child business identities or Parquet join identities.

The DB07 fixtures remain decision examples rather than release instances. DB08
encodes their accepted identity, authority, and conflict boundaries in the
[version-1 release schema contract](database-release-schema-contract.md); both
fixture suites remain independently validated.
