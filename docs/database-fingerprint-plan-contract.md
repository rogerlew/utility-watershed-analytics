# Database fingerprint and plan contract

Status: accepted version 1 contract

Date: 2026-07-17

This document defines the DB09 semantic fingerprint and base-specific plan
contract. It builds on the
[version-1 release schema contract](database-release-schema-contract.md) and
does not authorize materialization, deployment, rollback, artifact-provider
provisioning, or production access. Provider behavior is separately frozen by
the [artifact-store contract](database-artifact-store-contract.md).

## 1. Canonical bytes and digest

Version 1 canonicalization is deliberately small:

1. Parse JSON decimals exactly rather than through binary floating point.
2. Reject duplicate object keys. Normalize every object key and string value to
   Unicode NFC; a key collision introduced by normalization is also invalid.
3. Represent integers and exact decimals as the shortest non-exponent decimal
   string; normalize all zero forms to `"0"`.
4. Preserve booleans and null as JSON literals.
5. Sort object keys lexicographically by normalized Unicode value.
6. Preserve array order unless the subject rules below declare the array
   set-like and provide a stable sort key.
7. Emit UTF-8 JSON with no insignificant whitespace and one final newline.
8. Compute lowercase SHA-256 over those exact bytes.

Binary floating-point objects, non-finite numbers, non-string object keys, and
unsupported scalar types are invalid. Version 1 geometry inputs are not
canonicalized from coordinates. A materializer must first produce a canonical
CRS-qualified binary geometry artifact and use its content digest.

The implementation is `scripts/release_fingerprints.py`. Any change to these
rules requires a new `fingerprint_version` and coordinated data-contract
review; changing code without changing the version is invalid.

## 2. Semantic subjects

Each normalized subject includes `fingerprint_version: 1` and a subject tag.

| Subject | Included semantic state | Explicit exclusions and set ordering |
| --- | --- | --- |
| Artifact | Content SHA-256, exact bytes, and media type. | Transport URI and `verified` are excluded; validation must already have accepted them. |
| Run | Collection/watershed identity, current run ID, display name, aliases, role-keyed artifact fingerprints, optional transformation/RHESSys/capability fingerprints, expected counts, and bounds. | Aliases sort lexicographically; map key order is irrelevant. |
| Capability | Stable run identity, mode, serving base URI, geometry revision, required flags, and content/serving metadata for spatial, Parquet, and GeoTIFF assets. | Artifact transport URIs are excluded. Assets sort by role or scenario/variable/content digest; variables sort by name. |
| Watershed domain | Stable collection/watershed/run identity plus run and capability fingerprints for every active run. | Runs sort by collection, watershed, then run ID. Database IDs, audit rows, attempts, timestamps, and logs are excluded. |
| Release | Compatibility/materializer/toolchain state, exact collections and member-index content, stable target membership, exact removals, and reviewed lineage. | Release ID, creation timestamp, authentication reference, validation-report location, and artifact transport URIs are excluded. Collections, target keys, removals, aliases, lineage, predecessors, and successors use stable sorts. |

Semantic release fingerprints do not replace exact manifest hashes. A plan
records both: the exact manifest SHA detects any byte change to the reviewed
file, while the release fingerprint supports semantic comparison across
irrelevant formatting or ordering changes.

## 3. Plan coordinates

The schemas under `data-releases/schema/v1/plans/` define one closed common
shape and strict wrappers for:

- `forward`: a populated reviewed base to a populated target;
- `exact-inverse`: the forward target back to its populated base; and
- `empty-build`: literal `EMPTY` to a populated target for reconstruction
  proof.

Every plan pins:

- plan schema and fingerprint version;
- data and identity contract version;
- exact supported Django migration;
- materializer image digest and Git commit;
- populated base and target release IDs, exact manifest SHA-256 values,
  semantic release fingerprints, and watershed-domain fingerprints;
- sorted, unique per-watershed actions with exact before/after run and
  capability fingerprints, explicit change channels, and row-count deltas; and
- aggregate row-count deltas equal to the sum of actions.

No plan coordinate accepts a wildcard, `latest`, omitted fingerprint, partial
state, or inferred base. `EMPTY` is a literal closed object and is allowed only
for the empty-build plan.

## 4. Replay and inverse rules

Before fetching or staging an artifact, an executor must derive the observed
active state and compare the complete base object for exact equality. A
difference in release ID, manifest SHA, release fingerprint, or domain
fingerprint rejects with a base mismatch. Regenerating a plan for a new base is
a separate review action; weakening the comparison is not allowed.

An exact inverse:

- uses the forward target as its base and the forward base as its target;
- pins the canonical SHA-256 of the complete forward plan;
- keeps all contract, migration, fingerprint, and materializer coordinates;
- mirrors add/remove operations, swaps every before/after state, preserves
  change channels, and negates every row-count delta; and
- retains an unchanged run only when both run states are exactly equal and all
  deltas are zero.

An empty-build plan has only add actions from `EMPTY`. It is reconstruction
proof, not permission to clear or replace an existing database.

## 5. Proof and CI

Illustrative fixtures live under
`data-releases/fixtures/v1/fingerprint-plans/`. They contain no real release or
production membership. Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_fingerprint_plan_contract.py
PYTHONDONTWRITEBYTECODE=1 python -m unittest scripts.tests.test_fingerprint_plan_contract
```

The suite locks golden hashes for all five subjects, repeats the CLI in
independent processes, changes irrelevant formatting and set ordering, mutates
one semantic field per subject, validates all plan schemas, proves inverse and
empty-build relationships, and rejects a base differing only by its domain
fingerprint. `.github/workflows/data-contract-ci.yml` runs these gates alongside
the DB08 schema suite.
