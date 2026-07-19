# RHESSys artifact preparation contract

Status: accepted version 1

Date: 2026-07-18

DB19 implements the bounded preparation step between reviewed RHESSys source
coordinates and the immutable capability index defined by DB08. It uses the
DB12 local artifact client; on `forest1`, accepted artifacts remain backed by
the operator-owned `/wc1/utility-watershed-analytics-artifacts` filesystem.
No cloud provider, paid storage, production host, or runtime activation is part
of this contract.

DB28 extends the version-1 dynamic index with explicit scenario-specific
Parquet dataset keys and checksum-pinned query geometries. Real Gate Creek
requires multiple basin, hillslope, and patch datasets per scenario; uniqueness
is therefore enforced on dataset keys and scenario/role/variable query
coordinates rather than role alone. Each hillslope or patch coordinate must
have exactly one declared GeoJSON geometry for its scenario.

## Descriptor

`data-release prepare` routes `kind: "rhessys-capability"` to the DB19
preparer. The closed version-1 descriptor names exactly one collection,
watershed key, run ID, source revision, creation time, mode, geometry revision,
scenario/variable matrix, and exact source assets. Every source has a
credential-free HTTPS coordinate, SHA-256, byte count, and geometry revision.
Dynamic Parquets additionally name their exact dataset key and scenario;
query-geometry assets name their scale, scenario set, source CRS, and exact
GeoJSON source.

Modes are deliberately strict:

- `dynamic` requires at least one spatial-input GeoTIFF and Parquet and permits
  no precomputed GeoTIFF;
- `precomputed` requires exact GeoTIFF coverage of every declared
  scenario/variable pair and permits no dynamic assets; and
- `both` requires both families and exact precomputed coverage.

Scenario keys, scenario variables, spatial roles, Parquet dataset keys and
query coordinates, geometry scale/scenario coordinates, column names, and
GeoTIFF scenario/variable pairs are unique. Every Parquet declaration names
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
  Physical leaf names are bounded printable strings; only declared identity,
  year, and variable columns must satisfy runtime identifier rules. This
  permits harmless auxiliary columns in accepted real Parquets without making
  them queryable.
- GeoTIFF files must be classic TIFF with a bounded IFD, dimensions, bands,
  pixel scale, tiepoint, direct EPSG GeoKey, readable strip or tile range, and
  optional numeric GDAL nodata. Derived CRS, bounds, dimensions, bands, and
  nodata must match the descriptor, and a representative strip/tile byte is
  read. DB28 adds bounded axis-aligned ModelTransformationTag georeferencing
  because it occurs in the accepted Gate Creek source. Rotated/skewed
  transformations, BigTIFF, and indirect CRS keys still fail closed.
  Unrelated TIFF extension tags are ignored; required structural and GeoTIFF
  tags remain bounded and fail closed on unsupported encodings.
  A GeoTIFF `NaN` nodata sentinel is normalized to JSON `null`; finite nodata
  values remain exact.
- Query geometries must be non-empty GeoJSON FeatureCollections with finite
  coordinates. Their declared source CRS is retained for bounded runtime
  reprojection; DB28 additionally validates exact identifier joins.

Renamed variables, physical Parquet schema drift, corrupt/truncated rasters,
CRS mismatch, reversed or partial scenario declarations, and geometry revision
mismatch fail before an index is published.

## Publication and replay

Source bytes are checked against both declared size and SHA-256 before parsing.
Each accepted source is published content-addressed through DB12, fetched back
for verification, and referenced by immutable HTTPS URI, digest, size, media
type, and `verified: true`. The generated DB08 index includes scenarios,
scenario-specific physical Parquet columns, and exact query geometries in
addition to identity, mode, durable base URI, dynamic assets, and precomputed
assets.

Scenario identifiers follow the deployed runtime rule and preserve reviewed
case and underscores (for example `Pspread_fire_1yr_change`). Collection,
watershed, artifact-role, and dataset keys remain lowercase canonical keys.

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
validation; DB28–DB30 own real source locking and publication; DB30A/DB31 own
production adoption and planning.

DB19 synthetic proof does not establish that any inventory run is ready for
activation. Real RHESSys source URLs, scenario matrices, schemas, geometry
revisions, and durable copies remain pending inventory work.
