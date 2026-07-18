# RHESSys artifact preparation contract

Status: accepted version 1

Date: 2026-07-18

DB19 implements the bounded preparation step between reviewed RHESSys source
coordinates and the immutable capability index defined by DB08. It uses the
DB12 local artifact client; on `forest1`, accepted artifacts remain backed by
the operator-owned `/wc1/utility-watershed-analytics-artifacts` filesystem.
No cloud provider, paid storage, production host, or runtime activation is part
of this contract.

## Descriptor

`data-release prepare` routes `kind: "rhessys-capability"` to the DB19
preparer. The closed version-1 descriptor names exactly one collection,
watershed key, run ID, source revision, creation time, mode, geometry revision,
scenario/variable matrix, and exact source assets. Every source has a
credential-free HTTPS coordinate, SHA-256, byte count, and geometry revision.

Modes are deliberately strict:

- `dynamic` requires at least one spatial-input GeoTIFF and Parquet and permits
  no precomputed GeoTIFF;
- `precomputed` requires exact GeoTIFF coverage of every declared
  scenario/variable pair and permits no dynamic assets; and
- `both` requires both families and exact precomputed coverage.

Scenario keys, scenario variables, spatial roles, Parquet roles, column names,
and GeoTIFF scenario/variable pairs are unique. Every Parquet declaration names
its exact flat physical schema, spatial ID field, `year` column, variables,
units, year range, and activation requirement. Every raster declaration names
its CRS, bounds, dimensions, band count, nodata value, and activation
requirement. Asset geometry revisions must equal the capability revision.

## Structural inspection

The code-only image adds no GDAL, Arrow, provider SDK, or network storage
dependency. It performs the bounded checks needed before immutable copying:

- Parquet files must have a complete `PAR1` envelope, bounded Compact Protocol
  footer, positive row count, non-empty data region, and an exact flat leaf
  column name/physical-type match. The inspection reads representative data
  bytes but does not decode domain rows; DB21 owns value, join, and year-range
  validation.
- GeoTIFF files must be classic TIFF with a bounded IFD, dimensions, bands,
  pixel scale, tiepoint, direct EPSG GeoKey, readable strip or tile range, and
  optional numeric GDAL nodata. Derived CRS, bounds, dimensions, bands, and
  nodata must match the descriptor, and a representative strip/tile byte is
  read. BigTIFF, indirect CRS keys, and transform-only georeferencing fail
  closed until a reviewed contract revision adds them.

Renamed variables, physical Parquet schema drift, corrupt/truncated rasters,
CRS mismatch, reversed or partial scenario declarations, and geometry revision
mismatch fail before an index is published.

## Publication and replay

Source bytes are checked against both declared size and SHA-256 before parsing.
Each accepted source is published content-addressed through DB12, fetched back
for verification, and referenced by immutable HTTPS URI, digest, size, media
type, and `verified: true`. The generated DB08 index includes scenarios and
physical Parquet columns in addition to the existing identity, mode, durable
base URI, geometry, dynamic assets, and precomputed assets.

The receipt binds the canonical descriptor digest, exact source coordinates and
hashes, and generated index digest. Receipt replay makes no upstream requests
and must reproduce byte-identical index and receipt content. DB12's atomic
publication leaves neither an object nor a partial file after interruption.

The HTTPS base URI is the future serving coordinate recorded in the index; it
does not select or provision storage. The actual DB19 execution store is the
isolated `/wc1/.../v1/test` namespace and is removed after acceptance.

## Removal and successor boundary

Capability removal is an explicit set difference between the previously
reviewed and successor watershed-key sets. Omitted keys are returned in sorted
order and are never silently carried forward. DB19 does not mutate serving
state. DB19A owns reading materialized active capability state and removing
hard-coded/live-discovery authority; DB20–DB21 own materialization and domain
validation; DB30 owns real source locking and publication; DB30A/DB31 own
production adoption and planning.

DB19 synthetic proof does not establish that any inventory run is ready for
activation. Real RHESSys source URLs, scenario matrices, schemas, geometry
revisions, and durable copies remain pending inventory work.
