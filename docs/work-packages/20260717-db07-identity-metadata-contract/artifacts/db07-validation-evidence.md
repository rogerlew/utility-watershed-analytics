# DB07 Validation Evidence

Date: 2026-07-17

Host: `forest1`

Starting revision:
`518d3428c7d35e97b44e4c85a93cca7f10c56f4e`

Evidence mode: Mixed

## Reviewed inputs

Static review covered the completed DB06 domain audit and production summary,
the approved database inventory, architecture sections 5 and 8–10, the current
`Watershed`, `Subcatchment`, and `Channel` models, loader collection defaults,
field-source maps, child writers, API URL patterns, and client run-ID routes.

The review froze:

- four current collection keys and initial standalone watershed keys;
- reviewed batch-member key assignment rather than automatic suffix matching;
- stable watershed identity across rename, source replacement, and collection
  move;
- new successor keys and predecessor tombstones for split and merge;
- permanent run-ID aliases while referenced by retained compatibility state;
- current child business keys and future stable serialized child IDs;
- all 24 current watershed model fields for all four collections; and
- required-presence, explicit-null, derivation, and conflict behavior.

No external source, production host, database, runtime, or artifact store was
accessed.

## Fixture validator

Command:

```bash
python scripts/validate_identity_contract_fixtures.py \
  docs/work-packages/20260717-db07-identity-metadata-contract/artifacts/identity-contract-fixtures.json
```

Result:

- collections: 4;
- fields per collection: 24;
- scenarios: 12;
- accepted lifecycle scenarios: 9; and
- rejected conflict scenarios: 3.

Accepted scenarios cover retained, renamed, replaced, collection-moved, split,
merged, metadata-only, geometry-only, and deliberately removed watersheds.
Rejected scenarios cover ambiguous source-only identity, metadata-authority
conflict, and tombstoned-key reuse.

## Validator mutation tests

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest \
  scripts.tests.test_validate_identity_contract_fixtures -v
```

Result: 7 tests passed. The tests prove the accepted fixture, current
`Watershed` model field coverage, duplicate collection rejection, missing field
authority rejection, invalid key rejection, expected-decision mismatch
rejection, and split predecessor-key reuse rejection.

JSON parsing and Python bytecode compilation passed. Ruff was unavailable on
the host, and the earlier DB06 validation image was not present locally, so the
Ruff gate was recorded as unavailable rather than replaced with a new image
build.

## Documentation and boundary checks

- `git diff --check`: passed;
- relative Markdown links and referenced paths: passed;
- stale DB07 blocker/status scan: passed;
- JSON syntax: passed;
- literal credential assignment and prohibited-artifact scan: passed;
- generated `__pycache__` cleanup: passed; and
- changed-file review confirmed documentation, fixtures, validator, and its
  tests only.

The fixture is deliberately not a DB08 release schema. It contains illustrative
identities and fingerprints only, no production row payloads, credentials,
external mutable input, or activation authority.
