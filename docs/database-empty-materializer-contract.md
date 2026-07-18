# Strict Empty-Database Materializer Contract

Status: DB20 accepted

Date: 2026-07-18

This document defines the version-1 path from DB15 ledger rows and DB12-locked
ordinary artifacts through DB16 staging into an atomic clean serving build. It
is the only accepted EMPTY-base writer. DB23 must reuse its canonical staged
rows and serving mutation primitives when non-empty reconciliation is added.

## Ownership boundary

DB20 owns:

- `server.watershed.materializer.stage_locked_release`;
- `server.watershed.materializer.build_and_activate_empty_release`;
- `server.watershed.domain_mutations.apply_staged_empty_base`; and
- the bounded model writer and READY finalizer in
  `server.watershed.staging`.

The caller supplies an existing DB15 `DataReleaseAttempt`, validated
`DataRunState` rows, logical identities/current aliases, immutable
`DataArtifactLineage`, an exact DB16 space budget, local paths for every
consumed artifact role, and the reviewed actual-plan hash. DB20 does not assign
stable identities, create release/run fingerprints, download artifacts, or
derive a plan from filenames or current serving rows.

DB21 owns artifact/domain/application validation, fingerprints, reports, and
independent clean-build comparison through
`server.watershed.release_validation.validated_empty_build`, as frozen in the
[clean-build validation contract](database-clean-build-validation-contract.md).
DB22 owns base-aware reviewed plans.
DB23 owns non-empty reconciliation. DB20's Python entry points are executable
inside the server image; the code-only preparation image's `data-release build`
command remains unavailable until the later operator command can consume the
reviewed validator/planner outputs rather than inventing an interim input.

## Locked input

Every materialized member must exactly match one target-release run state. Its
path map contains exactly these required roles:

| Role | Media type | Use |
| --- | --- | --- |
| `metadata` | `application/json` | stable coordinates and normalized watershed metadata |
| `boundary` | `application/geo+json` | one watershed multipolygon |
| `subcatchments` | `application/geo+json` | typed Topaz/WEPP child geometry rows |
| `channels` | `application/geo+json` | typed Topaz/WEPP/order child geometry rows |
| `hillslopes` | `application/vnd.apache.parquet` | hillslope attributes by Topaz ID |
| `soils` | `application/vnd.apache.parquet` | soil attributes by Topaz ID |
| `landuse` | `application/vnd.apache.parquet` | land-use attributes by Topaz ID |

A run with a non-null capability fingerprint also supplies exactly one
capability declaration and one JSON index role backed by immutable lineage.
The index URI/checksum in its strict DB19A runtime configuration must equal that
lineage row. A run without a capability fingerprint may not supply one.

Before staging exists, every path must be a non-symlink ordinary file whose
media type, byte size, and streaming SHA-256 equal immutable lineage. File
device, inode, size, and modification time are reasserted after consumption.
The exact sum of locked input bytes must equal the artifact component of the
recorded DB16 capacity budget.

## Canonical staging

Members are processed by run ID. All staging rows reference the attempt,
immutable run state, and logical watershed identity.

- Metadata is capped at 1 MiB, requires the exact DB17 member shape, and must
  agree with collection key, watershed key, run ID, and permanent aliases.
  Source fields are normalized through the existing serving-field map; the
  staged payload contains serving field names only.
- Each boundary contains exactly one valid non-empty EPSG:4326 multipolygon.
  A DB21A legacy export may additionally carry exact main/simplified EWKB in
  reserved feature properties so source-independent inverse reconstruction
  preserves the existing serving bytes; ordinary source artifacts remain
  unchanged.
- Subcatchment and channel features are iterated through GDAL and normalized to
  valid EPSG:4326 multipolygons. Typed business keys and attempt-scoped database
  uniqueness reject absent, malformed, or duplicate entities.
- Parquet is opened by footer and consumed with `iter_batches`. Only the Topaz
  join and mapped fields are read. Topaz IDs must be non-null and strictly
  increasing, every batch must join exact staged geometry, and every required
  Parquet role must contain the run state's exact subcatchment count.
- Capability rows carry the run state's exact fingerprint and locked index
  coordinates. Serving application validates the complete DB19A public runtime
  configuration before insertion.

No complete GeoJSON collection, Parquet table, child-key set, or database
queryset is converted to an unbounded in-memory collection. Hash reads use
1 MiB chunks. Geometry features, Arrow records, staging inserts/updates, and
serving inserts remain at or below the caller's positive `batch_size`. The
default is 1,000.

Only after every run and release total matches the DB15 ledger does
`mark_staging_ready` atomically mark all rows `validated` and the staging state
`READY`. Repeated attempts over the same locked inputs produce the same
canonical row values independent of attempt IDs.

## EMPTY mutation and activation

`apply_staged_empty_base` locks and requires all of the following:

- the singleton is coherent `EMPTY` with no release;
- the reviewed attempt base is empty;
- all three serving domain tables are empty;
- the attempt is `applying` and its staging state is `READY`;
- release-wide and per-run watershed/child/capability counts are exact;
- every staged row is validated and every release run is represented once;
- every serving current alias points to the staged run ID; and
- no target-release capability row already exists.

The primitive maps only allowlisted canonical metadata/attributes, validates
each serving row, and inserts watersheds, subcatchments, channels, and strict
runtime capabilities in deterministic key order and bounded batches. It never
deletes, updates, or scans unrelated application tables.

`build_and_activate_empty_release` stages first, records the actual plan hash,
and then runs EMPTY application plus the existing DB15 `activate_release`
helper inside one outer database transaction. Readers therefore observe either
the prior empty state or the complete active release, never an accepted partial
build. This composition, not a standalone call that commits between apply and
activation, is the accepted clean-build operation.

DB21 strengthens that composition by running artifact and staged validators
before apply, then database and public-application validators after activation
inside the same outer transaction. A database or application validation
failure therefore rolls back the DB20 serving mutation and active pointer.

## Failure and recovery

Any missing, changed, malformed, unordered, duplicate, unmatched, count-wrong,
non-public capability, non-empty base, or activation error fails and releases
the whole DB15 attempt with a sanitized phase/summary.

Failures before READY may retain complete committed DB16 chunks for diagnosis.
They are never serving state. Failures during EMPTY apply or activation roll
back every serving and active-pointer mutation while retaining READY staging
for bounded DB16 cleanup/recovery. Retrying requires a new attributable attempt;
the failed attempt is immutable history.

## Accepted proof

Synthetic batch and standalone members in one release produced exactly two
watersheds, four subcatchments, two channels, and one strict SBS capability.
With `batch_size=1`, both staging and serving mutation reported a maximum batch
of one. Exact locked inputs produced equal canonical staging snapshots in two
independent attempts. A duplicate required Parquet join failed after diagnostic
staging without serving mutation, and a late invalid capability failed after
the serving inserts began but transaction rollback restored exact `EMPTY`.

The focused DB20/DB16 tests, complete 177-test server suite, Ruff, migration
drift check, and production server image build passed against disposable
PostGIS on forest1. No `wepp3`, real release/artifact namespace, or production
database was accessed or changed.
