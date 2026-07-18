# Database Staging and Recovery Contract

Status: DB16 accepted

Date: 2026-07-17

This document defines the attempt-scoped staging and recovery layer implemented
by migration `watershed.0010_attempt_scoped_staging`. It is preparation for a
later reconciler. It does not fetch, activate, reconcile, remove, back up, or
restore real data.

## Fixed logged tables

DB16 adds five ordinary logged PostgreSQL tables. Deployment creates no dynamic
table or activation-time DDL.

| Model | Purpose |
| --- | --- |
| `DataReleaseStagingState` | One attempt's capacity budget, observed space, staging lifecycle, row counts, diagnostic retention, and cleanup attempts/error. |
| `StagedWatershed` | Typed attempt/run/logical identity, run ID, source fingerprint, normalized EPSG:4326 geometry, metadata payload, and validation state. |
| `StagedSubcatchment` | Typed attempt/run/logical identity, accepted Topaz business key, geometry, normalized attributes, fingerprint, and validation state. |
| `StagedChannel` | Typed attempt/run/logical identity, accepted Topaz/WEPP/order business key, geometry, normalized attributes, fingerprint, and validation state. |
| `StagedRunCapability` | Typed attempt/run/logical identity, RHESSys type/mode, durable base/index references, immutable hashes, public configuration, and validation state. |

Every target row references both the DB15 attempt and immutable target
`DataRunState`. Model validation requires their releases and logical watershed
identities to agree. Database uniqueness follows the DB14 logical keys inside
one attempt. Explicit attempt/status or attempt/watershed indexes support
validation and cleanup.

Metadata and denormalized child attributes are normalized JSON payloads because
the later reconciler owns their serving-field mapping. Business identities,
geometry, fingerprints, validation state, and capability references remain
typed columns. Secret-bearing payload/configuration keys reject before insert.

## Capacity preflight

No staging row may be written before one explicit capacity budget is recorded:

```text
required = artifacts + staging tables + indexes + verified backup + WAL + margin
```

All six components are non-negative and independently recorded. Exact fit
passes. One byte short records `SPACE_REJECTED`, fails and releases the attempt,
and leaves every staging table empty. The helper can read free bytes for a host
path, but production must provide authoritative available capacity for every
relevant database and artifact filesystem; forest1 test values are not wepp3
capacity evidence.

## Bounded loading

`load_staging_rows` accepts iterables and never converts a complete dataset to a
list. It reads at most `batch_size` records, with a default of 1,000. Before
each chunk commit it validates row fields and cross-record ownership, verifies
and extends the DB15 lease, and then uses one `bulk_create` transaction. The
database enforces uniqueness for the whole chunk.

A bad or duplicate current chunk rolls back entirely. Previously committed
chunks remain in logged tables if parsing, validation, the release-tool process,
or its database connection fails. This is intentional diagnostic state, not
serving state. The staging-state counts are updated in the same transaction as
each successful chunk.

## Recovery and cleanup

DB15 remains the only attempt and lease authority. DB16 never grants takeover.
`recover_expired_attempts` finds expired `planning`, `staging`, and `applying`
attempts and, one at a time:

1. locks and marks the attempt `failed` in a separate transaction;
2. preserves the DB15 release, run, artifact, capability, attempt, and active
   pointer history;
3. retains staging rows until `retention_until`; and
4. after retention, deletes by exact attempt ID from this allowlist and order:
   staged capability, channel, subcatchment, watershed.

The staging-state audit row remains. Successful cleanup sets `CLEANED`, zeroes
its row counts, and clears its error. A deletion failure increments
`cleanup_attempts`, stores one sanitized bounded error, and remains
`CLEANUP_PENDING`. `retry_pending_cleanup` uses the same exact allowlist.

No cleanup path references `watershed_watershed`, `watershed_subcatchment`,
`watershed_channel`, `ActiveDataRelease`, release history, Django auth/session,
or any non-staging table. Focused integration proof preserves all of them while
recovering an expired successor attempt.

## Compatibility and next boundary

DB16 is additive and old application code ignores these tables. Migration
forward/reverse on synthetic data matching the accepted production aggregate
preserved serving counts and child IDs. Production migration and capacity
claims require separate authority.

DB16 does not decide exact source membership, transform artifacts, compare a
reviewed plan, or mutate serving rows. DB17 owns strict source resolution; the
later reconciler packages own staged validation, plan recomputation, activation,
and cleanup orchestration through the release-tool command surface.
