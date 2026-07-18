# Database release schema contract

Status: accepted version 1 contract

Date: 2026-07-17

This document defines the machine-readable release representation accepted by
DB08. It encodes the identity and metadata decisions in the
[DB07 contract](database-identity-metadata-contract.md) without choosing an
artifact provider, fingerprint algorithm, deployment plan, or production
release membership.

## 1. Canonical format and version boundary

JSON is the canonical representation. Every schema uses JSON Schema Draft
2020-12 and has a stable `$id` below
`https://firewisewatersheds.org/schemas/data-release/v1/`. The version-1 suite
is stored in `data-releases/schema/v1/`:

| Schema | Authority |
| --- | --- |
| `artifact-reference.schema.json` | Immutable artifact location, SHA-256, byte size, media type, and verified assertion. |
| `batch-member-index.schema.json` | Exact collection membership, stable identity, required watershed artifacts, expected counts, and bounds. |
| `compatibility-envelope.schema.json` | Data, identity, artifact, migration, materializer, and toolchain compatibility. |
| `release-manifest.schema.json` | Release identity, collections, exact target keys, exact removals, reviewed lineage, and validation evidence. |
| `rhessys-capability-index.schema.json` | Dynamic and precomputed RHESSys asset families keyed by stable watershed identity. |
| `transformation-lineage.schema.json` | Immutable inputs/output, code/configuration identity, field authority decisions, and reconciliation counts. |
| `validation-report.schema.json` | Sanitized, machine-readable checks and aggregate results. |

`schema_version`, `data_contract`, `identity_contract`, and
`artifact_contract` accept version `1` only. A consumer must reject an unknown
version rather than guess compatibility. DB09 owns fingerprint and
base-specific deployment-plan versions.

## 2. Artifact and authentication boundary

Every artifact reference requires:

- an HTTPS URI with a path and no user information, query, or fragment;
- a lowercase 64-character SHA-256 digest;
- a positive byte count and explicit media type; and
- `verified: true`.

Release documents contain secret references only. The sole authentication
shape is `{"secret_ref": "UPPERCASE_ENV_STYLE_NAME"}`. Passwords, tokens,
credentials, raw secrets, credential-bearing URLs, and provider-specific
access material are invalid. The reference is resolved only by an authorized
future execution environment; DB08 does not resolve it.

## 3. Exact identity and removal rules

The batch member index is the exact desired collection membership. Every
member carries one stable `watershed_key`, one current `runid`, aliases,
required watershed artifact references, and expected counts and bounds. The
release repeats the ordered stable keys and expected count so validation can
compare the release and index before any materialization.

Collection keys, target watershed keys, current run IDs, removal keys, lineage
event keys, and other role-specific identities must be unique in their scope.
An expected removal names one exact stable watershed key. Wildcards are
structurally invalid, and a key cannot appear in both the target membership and
the removal set. Split, merge, replacement, move, and removal lineage is
explicit and requires `reviewed: true`.

## 4. Capability, transformation, and report rules

RHESSys mode controls required asset families:

- `dynamic` requires at least one spatial input and one Parquet asset;
- `precomputed` requires at least one GeoTIFF asset; and
- `both` requires all three families.

Transformation records pin every input, the output, code commit, configuration
hash, join keys, field authority decisions, and counts. Field decisions are
unique and outputs cannot reuse an input checksum. Validation reports use
sanitized summaries, unique check codes, ordered timestamps, and an overall
status consistent with their checks.

## 5. Structural and semantic validation

JSON Schema owns closed object shapes, required fields, formats, constants,
patterns, and conditional asset requirements. The bounded validator at
`scripts/validate_release_schemas.py` owns uniqueness and cross-record rules
that Draft 2020-12 cannot express cleanly, plus a recursive credential and URI
boundary check.

Run the same gates used by CI:

```bash
python -m pip install jsonschema==4.23.0
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_release_schemas.py
PYTHONDONTWRITEBYTECODE=1 python -m unittest scripts.tests.test_validate_release_schemas
```

Fixtures in `data-releases/fixtures/v1/` are deliberately illustrative. The
valid suite covers every schema exactly once. The negative suite proves
duplicate identities, wildcard and overlapping removals, unverified inputs,
missing RHESSys assets, incompatible versions, and a raw authentication token
are rejected. Adding or removing a schema or required negative category makes
the suite fail until coverage is reconciled.

## 6. Successor boundaries

DB09 may add canonical fingerprints and base-specific forward, inverse, and
empty-build plan contracts while referencing these version-1 records. DB10 may
select a project-controlled artifact provider and retention/security policy.
Neither successor may weaken immutable verification, exact membership,
identity, removal, or credential boundaries without a new reviewed contract
version.
