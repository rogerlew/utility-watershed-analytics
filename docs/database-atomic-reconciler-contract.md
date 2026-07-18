# Database atomic reconciler contract

Status: accepted DB23 contract

Date: 2026-07-18

DB23 applies one exact DB22 forward plan from a populated active release to a
complete DB20-staged target. It owns the short database activation transaction,
not artifact preparation, production orchestration, backup, rollback, or
post-commit recovery.

## Inputs and entry point

`reconcile_and_activate_release` in
`server/server/watershed/materializer.py` uses the existing DB20 artifact
verification and `stage_locked_release` path, transitions the attempt to
`applying` with the canonical forward-plan digest, and calls
`apply_staged_release`.

The target staging set is complete rather than a patch. Every staged row must
be validated; total and per-run watershed, child, and capability counts must
exactly match the immutable target ledger. The attempt must name a populated
reviewed predecessor, a live target release, and identical reviewed/actual
plan digests.

## Activation transaction

The reconciler performs this sequence in one PostgreSQL transaction:

1. acquire the fixed transaction-scoped reconciliation advisory lock;
2. defer foreign-key checks needed for an atomic run-ID replacement;
3. lock the singleton active-release row, attempt, staging state, affected
   identities, watersheds, and children;
4. regenerate the complete DB22 plan from the observed active base and require
   exact document equality with the reviewed plan;
5. reassert base release/manifest/domain fingerprints, contract/materializer
   compatibility, and exact serving/capability row counts;
6. apply only the sorted reviewed actions from complete target staging;
7. install the target release's capability rows;
8. activate the target and supersede the previous release; and
9. recompute exact target row counts and serving-domain fingerprint before
   commit.

Any error rolls back serving rows, aliases, identity status, capabilities,
release status, attempt success, and the active pointer together. The outer
materializer records a sanitized failed attempt after the activation
transaction rolls back.

## Reconciliation rules

- `retain` leaves watershed and child serving rows untouched.
- Metadata changes clear all authoritative metadata fields and apply the
  complete canonical staged values to the existing watershed row.
- Geometry changes update canonical geometry and regenerate simplified
  geometry with the versioned materializer tolerance. Exact simplified
  geometry carried by a DB21A replay remains exact.
- Child changes reconcile subcatchments by stable logical watershed plus
  `topazid`, and channels by logical watershed plus
  `topazid`/`weppid`/`order`. Matching rows update in place, preserving their
  public database IDs; only absent keys delete and only new keys insert.
- A run replacement changes the watershed run-ID primary key and child foreign
  keys under deferred constraints, preserving the logical watershed and
  matching child IDs. Historical aliases remain bound and the target run alias
  becomes current inside the same transaction.
- An addition creates one active identity-serving watershed and its exact
  staged children. A removal deletes only the reviewed identity's serving rows,
  retires that persistent identity, and leaves its historical aliases
  non-current.
- Target capability rows are rebuilt from validated staging. Prior-release
  capability ledger rows remain for history and become non-serving when the
  pointer advances.

The reconciler never discovers membership at runtime, applies an unreviewed
removal, mutates unrelated application tables, or treats a base/plan/fingerprint
difference as a warning.

## Reader boundary

Parsing and staging occur before activation, while readers continue to see the
old committed release. PostgreSQL MVCC keeps all uncommitted reconciliation
changes invisible. After commit, the pointer, domain rows, aliases, capability
visibility, release status, and attempt result become visible as the complete
new state. A reader cannot observe an intermediate mixture.

DB24 owns idempotency, the full failure/recovery matrix, and exact inverse
rollback. DB23's successful forward activation is not production authority.
