# Database source preparation contract

Status: implemented version 1

Date: 2026-07-17

DB17 implements strict source resolution for the code-only release tool. It
turns reviewed standalone or batch source coordinates into immutable DB12
objects and a deterministic
[DB08 exact member index](database-release-schema-contract.md). It does not
authorize a real release or production deployment.

## 1. Reviewed descriptor

Preparation accepts one JSON descriptor with:

- `schema_version: 1` and `kind` equal to `standalone` or `batch`;
- stable collection key, source revision, and fixed whole-second UTC creation
  time;
- an ordered non-empty member map containing reviewed stable watershed key,
  exact source run ID, display name, and aliases;
- either all six explicit standalone source URLs or a direct batch master URL
  plus five `{runid}` source templates; and
- optional authentication as an uppercase environment `secret_ref` only.

All source and artifact-base URLs are credential-free HTTPS URLs without user
information, query strings, or fragments. A custom batch master filename is
represented by its exact URL; the preparer does not derive or guess a name.

The stable identity map is authority. DB17 does not normalize a suffix into a
stable key or accept a newly discovered member implicitly.

DB28 adds one closed batch-master identity option for a broader public
FeatureCollection: an exact top-level feature-ID location and an exact run-ID
prefix. The preparer filters only that prefix and still requires the resulting
set to equal the complete reviewed member map. This supports the public
Firewise Watersheds aggregate without treating unrelated collections as extra
Victoria members or inferring stable keys.

## 2. Exact source resolution

For a batch, the master must be a non-empty GeoJSON FeatureCollection. Every
feature requires one unique string `runid`, and the discovered run-ID set must
equal the reviewed member map exactly. Empty, missing, extra, or duplicate
members fail the preparation before an index is published.

For a standalone run, exactly one reviewed member supplies explicit boundary,
subcatchment, channel, hillslope, soil, and land-use URLs. Every required URL
must succeed; there is no optional fallback or warning path.

The default transport streams each response to a new private temporary file,
requires a successful HTTP status, and verifies `Content-Length` when present.
A short declared transfer is an integrity failure. No response writes directly
over an immutable object or trusted cache entry.

## 3. Format boundary

GeoJSON inputs must be non-empty FeatureCollections with feature objects,
property objects, supported non-empty geometry, finite coordinates, and WGS84
coordinate bounds. Credential-bearing property keys are rejected.

Parquet inputs must have both `PAR1` markers and a footer length that resolves
inside the complete file. This is deliberate code-only envelope validation;
DB21 owns dataset-specific column, type, join, CRS, and semantic validation.

The preparer computes boundary bounds plus subcatchment and channel counts. It
creates deterministic metadata JSON for each member and, for batches, a
canonical one-feature boundary artifact from the locked master.

## 4. Immutable publication

All raw required inputs and generated member artifacts are published with
DB12's `ArtifactClient`, then fetched again by digest before the DB08 index is
accepted. Physical bytes remain in the operator-owned forest1 namespace. Index
references use the caller-supplied public credential-free HTTPS artifact base
and contain exact SHA-256, bytes, media type, and `verified: true`.

The final exact member index is canonical UTF-8 JSON with sorted object keys,
compact separators, and one trailing newline. It preserves reviewed member
order and the descriptor's fixed timestamp. It is itself published immutably.

## 5. Receipt and replay

The canonical source receipt records:

- the normalized descriptor SHA-256;
- final member-index SHA-256; and
- every source role, run ID, URL, SHA-256, byte count, and media type.

It never records an authorization header or secret value. Replay requires the
receipt descriptor and source coordinates to match exactly, fetches all inputs
from DB12 by digest, and makes no upstream request. Authentication is therefore
not required for replay. The reconstructed member-index bytes and digest must
equal the receipt or replay fails.

## 6. Command boundary

DB17 activates:

```bash
data-release prepare \
  --descriptor /inputs/source-descriptor.json \
  --store-namespace /artifacts/test \
  --cache-root /cache \
  --artifact-base-uri https://artifacts.example.test \
  --output-index /outputs/member-index.json \
  --output-receipt /outputs/source-receipt.json
```

`--replay-receipt` replaces upstream access with exact immutable receipt
replay. Output files must not already exist. Results report only aggregate
counts and artifact hashes through DB11's stable JSON event envelope.

DB17 does not change the legacy runtime loader. NASA enrichment, RHESSys
indexes, materialization, full validation, planning, database mutation,
rollback, and production orchestration remain successor work.

DB18 now adds one closed batch-descriptor extension for the inventory-defined
NASA 202606 `WWS_Code` transform. It checksum-pins the enrichment input,
preserves target membership/run IDs/geometry, and publishes DB08 report and
lineage artifacts as defined by the
[NASA enrichment contract](database-nasa-202606-enrichment-contract.md).
