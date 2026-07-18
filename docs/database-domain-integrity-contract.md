# Watershed Domain Integrity Contract

Status: DB14 accepted

Date: 2026-07-17

This document defines the constraints and ownership boundary implemented by
DB14. It extends the DB13 additive identity schema without making logical links
non-null and without changing production.

## Enforced identities

Migration `watershed.0008_domain_integrity_constraints` installs these rules:

| Entity | Enforced rule |
| --- | --- |
| Collection | `key` is lowercase ASCII kebab case. |
| Watershed identity | A non-null `watershed_key` is lowercase ASCII kebab case. |
| Watershed identity status | Status is `active` or `retired`. |
| Subcatchment compatibility identity | `(watershed_id, topazid)` is unique. |
| Subcatchment logical identity | `(logical_watershed_id, topazid)` is unique when the logical link is non-null. |
| Channel compatibility identity | `(watershed_id, topazid, weppid, order)` is unique. |
| Channel logical identity | `(logical_watershed_id, topazid, weppid, order)` is unique when the logical link is non-null. |

Compatibility identities remain enforced while DB13's old child foreign keys
exist. Logical uniqueness is partial because DB13 intentionally leaves
unreviewed logical links nullable during expansion. A later contraction must
first prove every logical link and watershed key is assigned.

Before adding constraints, the migration runs aggregate checks for duplicate
compatibility and logical keys, child/parent logical-link mismatch, invalid
stable-key formats, and invalid identity status. It reports only finding codes
and counts. It does not select or log row identities.

## Analytical joins

Hillslope, soil, and land-use Parquet inputs join to the denormalized
`Subcatchment` row by Topaz identity. Each input must contain exactly one of the
accepted Topaz column spellings and must contain no null or duplicate Topaz
values. The loader rejects the whole input before mapping when that identity is
missing or ambiguous.

One `Subcatchment` row continues to own hillslope, soil, and land-use fields.
DB14 does not add normalized analytical tables or infer a different join key.

## Ownership boundary

Data reconciliation owns exactly these serving tables:

1. `watershed_channel`;
2. `watershed_subcatchment`;
3. `watershed_watershed`.

That order is also the allowed delete order for a bounded rebuild. The
executable registry is `server.watershed.domain_ownership`.

The following identity tables persist across a serving rebuild and are never
wholesale rebuild targets:

- `watershed_watershedcollection`;
- `watershed_watershedidentity`; and
- `watershed_watershedrunalias`.

All Django auth, admin, session, migration, observability, PostGIS, and other
non-watershed tables persist by default. A future release ledger or capability
table must declare its own ownership and deletion behavior before a reconciler
may mutate it.

## Deletion behavior

Django may cascade from `Watershed` to `Subcatchment` and `Channel`. PostgreSQL
foreign keys reject a raw parent delete until child rows are removed, so a raw
rebuild must follow the explicit child-first order. References to collection,
logical identity, and run alias rows use protected foreign keys; serving data
cannot silently remove persistent identity history.

## Compatibility and rollout

DB14 is additive. It does not remove legacy keys, make logical links non-null,
create release-ledger models, or authorize a production migration. Production
application belongs to a later package with its own backup, lock budget,
maintenance, and rollback authority.

The isolated production-shaped rehearsal used synthetic data matching the
accepted DB06 aggregate: 126 watersheds, 195,457 subcatchments, and 86,895
channels. Forward and reverse migration preserved counts and child IDs;
duplicate, orphan, and invalid-key probes failed; and a transactional
three-table rebuild preserved identity, auth, and session rows.
