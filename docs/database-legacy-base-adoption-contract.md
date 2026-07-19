# Legacy-base export and adoption contract

Status: DB21A accepted

Date: 2026-07-18

This contract defines the mechanism for turning an unmanaged populated
watershed database into a reviewed baseline without rewriting its serving rows.
Actual production capture/adoption remains DB30A and requires separate
authority.

## Reviewed identity assignment

`assign_reviewed_identities` is an explicit prerequisite, not part of adoption.
Its reviewed mapping must cover every current run exactly once, use unique
stable collection/watershed keys, and declare the complete alias set. It creates
or reuses identities/aliases and assigns the watershed and both child tables
atomically. Migration-generated provisional identities may be rekeyed in place
only when they are one-to-one with the exact serving membership, contain no
alias outside the reviewed set, and retain the serving run as their current
alias. This preserves their UUID and every domain link while adding the reviewed
successor/history aliases. Any conflict rolls the entire assignment back.

Once exported, adoption requires those exact identities and current aliases;
it never changes a watershed, subcatchment, channel, identity, or alias.

## Canonical export

`export_legacy_base` writes a deterministic version-1 manifest and immutable
objects below:

```text
objects/sha256/<first-two-hex>/<full-sha256>
```

Existing objects are accepted only when their bytes match the content key.
Publication uses a private temporary file and exclusive hard link. The manifest
records exact membership, identities/aliases, counts, reviewed bounds,
contracts/migration/materializer coordinates, DB21 domain/capability
fingerprints, and every artifact reference.

Each run exports the DB20 metadata, boundary, subcatchment, channel, and three
Parquet roles. Exact CRS-qualified EWKB properties preserve serving and
simplified geometry bytes across GeoJSON reconstruction; ordinary DB20 inputs
without those optional properties retain their existing normalization behavior.
Capability bootstrap indexes and all declared runtime assets are copied into
the same content-addressed baseline. The export therefore does not depend on a
later upstream source fetch.

`load_legacy_baseline` reloads the manifest by exact digest. Artifact checksum,
size, path, migration, and manifest checks run again before ledger installation,
adoption, or rollback.

## Rebuild path

`install_baseline_ledger` is allowed only with coherent `EMPTY` and empty
serving tables. It creates the immutable DB15 release/run/artifact ledger and
reviewed identities, but no serving capability rows. `materialization_members`
then maps the exported objects to the existing DB20/DB21 build path. There is no
second rebuild writer.

The accepted synthetic proof deleted the source database rows and rebuilt from
only the exported content-addressed objects. Watershed metadata, exact main and
simplified EWKB, child business fields/geometry, capabilities, counts, and both
DB21 fingerprints matched the pre-export base.

## Guarded adoption

`adopt_legacy_base` and the `adopt_legacy_base` Django management command require:

- coherent `EMPTY` with populated serving rows and either no release ledger or
  one exact validated retained ledger for the reviewed rolled-back baseline;
- exact baseline/serving run membership and already-reviewed identities;
- supported version-1 contracts and the applied current watershed migration;
- every immutable object at its reviewed size and SHA-256; and
- recomputed domain/capability fingerprints equal to the reviewed baseline.

Inside one transaction, adoption locks the active singleton, creates the
immutable release/run/artifact ledger, inserts only the exact reviewed
capability-bootstrap set, recomputes fingerprints, records an attributable DB15
attempt, and activates the release. Failure rolls back the ledger, capabilities,
attempt, and pointer. Pre-existing domain and unrelated application rows are
never written.

## Exact rollback

`rollback_legacy_adoption` and its management command require the exact active
release ID, manifest hash, serving fingerprints, and capability-bootstrap
membership. Rollback deletes only those capability rows, returns the singleton
to coherent `EMPTY`, restores the release to validated history, and marks the
adoption attempt rolled back. Immutable ledger/artifact history remains for
review and later plans. The DB19A bounded legacy fallback is observable again
because the active state is `EMPTY`.

No rollback proceeds after domain, capability, pointer, or manifest drift.

An exact retained ledger may be re-adopted without deleting immutable history.
The operation re-verifies the manifest, release/run/lineage rows, identities,
aliases, serving and capability fingerprints, and absence of conflicting
capabilities before recreating only the reviewed capability rows, recording a
new attributable attempt, and activating the retained release. Any drift fails
closed; a retained ledger is never treated as generic permission to replace or
repair metadata.

## Authority boundary

DB21A used synthetic rows and temporary objects on forest1 with disposable
PostGIS. It did not contact `wepp3`, capture real production rows, write the
`/wc1` production namespace, adopt a real base, or change a production service.
DB30A must separately review the actual identity mapping, capability bootstrap,
artifact destination, fingerprints, schema, backup, and rollback rehearsal.
