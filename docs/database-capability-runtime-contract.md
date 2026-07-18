# Database Capability Runtime Contract

Status: DB19A accepted

Date: 2026-07-18

This document defines how the public application resolves RHESSys and soil burn
severity (SBS) serving state. It does not authorize production migration,
release adoption, or publication of real artifacts.

## State boundary

The `ActiveDataRelease` singleton is checked before any capability lookup.

- In `EMPTY`, RHESSys compatibility is limited to the exact reviewed run/mode
  allowlist in `server.watershed.runtime_capabilities`. SBS compatibility
  requires an existing serving `Watershed` row. Each accepted fallback emits a
  sanitized `capability.legacy_fallback` event.
- In `ACTIVE`, only an exact `RunCapability` belonging to the pointed release
  can expose a feature. Missing, disabled, non-public, malformed, mismatched, or
  wrong-release rows fail closed and never fall back.
- The singleton transition therefore removes all legacy eligibility in the same
  transaction that makes materialized capabilities visible.

Legacy discovery, presentation registries, run-derived WEPPcloud download URLs,
and the legacy query engine are permitted only behind the `EMPTY` branch. They
cannot grant `ACTIVE` eligibility or supply an undeclared active asset.

## Public configuration

Migration `watershed.0011_capability_runtime_types` adds `sbs` to the accepted
capability types. RHESSys continues to support `dynamic`, `precomputed`, or
`both`; SBS is exactly `precomputed`.

Runtime configuration is credential-free public metadata. Both capability
types declare an enabled flag, public/disabled access policy, immutable index
URI and SHA-256, and geometry revision. RHESSys additionally declares exact
scenarios, variables, year ranges, spatial inputs, GeoTIFFs, Parquets,
geometries, CRS values, render metadata, and checksum/size-pinned artifact
references. SBS declares one checksum/size-pinned TIFF reference.

Every materialized artifact must:

- use a credential-free HTTPS URI below the capability's durable base URI;
- carry exact SHA-256, byte size, media type, and verified state;
- match declared scenario, variable, year, geometry, and mode relationships;
  and
- pass checksum and byte-count verification before server-side JSON, Parquet,
  or download consumption.

Invalid configuration is logged as a sanitized rejection and exposes no
configuration or feature.

## Server paths

One resolver owns catalog, spatial-input tile, output tile, geometry, dynamic
query, SBS tile/download, and capability-summary eligibility. Materialized
tiles use exact declared TIFF URIs. Geometry and SBS downloads are checksum
verified. Dynamic requests contain semantic dimensions only; the server selects
one declared Parquet and performs bounded column/filter reads. Clients cannot
submit a path, URI, dataset name, or SQL expression.

The public capability summary exposes serving state, source, mode, access
policy, immutable index coordinates, geometry revision, scenarios, and
variables. It does not expose artifact references or runtime configuration.

## Client ownership

The client receives RHESSys eligibility, mode, scenarios, variables, spatial
scales, year ranges, descriptions, and geometry revisions from server APIs. SBS
controls and download visibility use the capability summary. The client has no
RHESSys run allowlist, scenario catalog, variable catalog, Parquet path map, or
patch-geometry mapping and does not construct RHESSys/SBS WEPPcloud URLs.

The separate operator-selected backup and artifact infrastructure remains
`forest1:/wc1` under the DB10–DB12 contracts. DB19A selects no external provider
and creates no paid service.

## Proof and rollout boundary

Synthetic tests exercise both sides of the atomic `EMPTY` to `ACTIVE`
transition, exact allowlisting, existing-watershed SBS fallback, malformed and
disabled rows, declared catalog/tiles/geometry/query/downloads, no-discovery
materialized reads, checksum-verified Parquet aggregation, and sanitized client
requests. Full server and client regression suites pass.

DB19A changes repository behavior only. DB27A owns the separately authorized
production compatibility migration/code rollout, and DB30A owns activation of
a reviewed materialized release.
