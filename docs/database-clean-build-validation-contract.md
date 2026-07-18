# Clean-build validation and fingerprint contract

Status: DB21 accepted

Date: 2026-07-18

This document defines the validation required around a DB20 empty build and the
serving fingerprints used to prove reproducibility. It does not authorize a
real release, production access, non-empty reconciliation, or adoption of a
legacy database.

## Ownership and entry point

DB21 owns `server.watershed.release_validation.validated_empty_build` and the
five validation layers it composes. The entry point accepts an existing DB15
attempt, the same locked members and capacity budget consumed by DB20, the
reviewed actual-plan hash, exact validator coordinates, reviewed bounds for
every run, optional removed run IDs, and an optional representative RHESSys
probe.

DB21 does not define another writer. It calls the DB20 staging and EMPTY-base
mutation primitives and DB15 activation. DB22 owns reviewed base-specific
plans, DB21A owns legacy-base export/adoption, and DB23 owns non-empty
reconciliation.

## Validation layers

All required checks are fatal. A failed check cannot become a warning.

1. **Artifact validation** requires an immutable lineage row for every supplied
   path; a credential-free HTTPS URI with no query or fragment; exact media
   type, byte count, and streaming SHA-256; a non-symlink ordinary file that is
   unchanged through use; and a non-HTML body. DB20 remains responsible for
   parsing the declared JSON, GeoJSON, and Parquet shape.
2. **Run and release validation** requires READY DB16 staging, exact reviewed
   bounds membership, exact expected/actual release and per-run counts, and
   exact staged capability counts. Every geometry must be valid, non-empty
   EPSG:4326 data within world bounds. Watershed extents must be within `0.001`
   degrees of the reviewed extent, every child must be covered by its
   watershed, and the summed subcatchment-to-watershed planar area ratio must
   be between `0.01` and `2.0`. The DB20 three-Parquet Topaz joins must be
   complete for every staged subcatchment.
3. **Database validation** requires the singleton to name the exact target
   release and manifest, serving counts to equal the immutable release ledger,
   and every watershed, subcatchment, and channel to carry its logical
   identity. It computes both serving fingerprints.
4. **Application validation** exercises the public watershed GeoJSON list,
   stable-key detail, subcatchment and channel GeoJSON, and capability summary.
   Every reviewed removed run must return `404`. When a RHESSys probe is
   supplied, the validator reads the materialized catalog and executes one
   semantic public query whose rows must exactly match the reviewed result.
5. **Report validation** produces the closed version-1 DB08 validation-report
   shape. Report/check keys, subject, validator commit/image digest, counts,
   statuses, summaries, and timestamp order are checked before serialization.
   Summaries use the DB15 sanitizer. Atomic publication creates a new path by
   hard link and refuses overwrite or symlink targets.

## Serving fingerprints

DB21 uses the exact DB09 version-1 canonical byte implementation in
`server/server/watershed/fingerprint_contract.py`. The existing
`scripts/release_fingerprints.py` command imports and re-exports that module;
the DB09 golden and mutation suite prevents script/server drift.

The domain fingerprint includes, in stable collection/watershed/run order:

- logical collection and watershed keys plus current run ID;
- canonical watershed geometry, simplified geometry, and allowlisted serving
  metadata;
- ordered subcatchment business keys, geometry, and allowlisted attributes;
- ordered channel business keys and geometry; and
- the target release's strict runtime capabilities associated with each run.

The capability fingerprint independently includes every target capability in
stable logical/run/type order, its mode, durable base and index coordinates,
immutable capability fingerprint, and complete runtime configuration.

Geometry is hashed as CRS-qualified EWKB hex. Serving floats are converted
through decimal text before DB09 canonicalization. Querysets use explicit
logical ordering and `iterator(chunk_size=1000)`; child and capability sets are
folded into bounded sequence digests rather than loaded as complete lists.

Database primary keys, attempt/report IDs, timestamps, leases, audit rows,
logs, and other non-serving state are excluded. A change to DB09 canonical
rules requires a new fingerprint version; a change to the included DB21
serving subject requires coordinated contract and fixture review.

## Atomic acceptance and failure

Artifact and staged validation finish before serving mutation. DB20 EMPTY
apply, DB15 activation, database validation, and application validation share
one outer transaction. Readers therefore see either the prior EMPTY state or a
complete build that passed database and application checks. A failure in that
transaction rolls back serving rows and the active pointer. The attempt is
marked failed with a sanitized phase and summary; diagnostic DB16 staging may
remain for bounded cleanup.

`validated_empty_build` returns the DB20 staging/apply result, both serving
fingerprints and counts, and a sanitized validation report. Report publication
is a separate explicit action so a caller can choose its reviewed immutable
destination.

## CI reproducibility proof

`.github/workflows/server-ci.yml` builds the production server image, runs the
full server suite, then invokes the same synthetic locked release in two
separate container/test-database lifecycles. Each build writes only the
canonical fingerprint/count document. CI requires byte-for-byte equality and
records its SHA-256.

The accepted forest1 proof produced two identical documents with two
watersheds, four subcatchments, two channels, and one capability. Negative
tests reject credential-bearing artifact URLs, saved HTML error bodies,
uncovered child geometry, and invalid/duplicate report publication without
accepting serving state. The public RHESSys proof reads checksum-pinned Parquet
and returns its exact reviewed values.

No `wepp3`, real manifest, real artifact namespace, production database, or
production service was accessed or changed by DB21.
