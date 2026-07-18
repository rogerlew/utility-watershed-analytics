# DB08 validation evidence

Date: 2026-07-17

Environment: `forest1`, repository `/workdir/utility-watershed-analytics`,
branch `agent/database-backup-deployment-spec`, starting revision
`c9ab4c90d42817da6343557acb82add5e087c69e`

Evidence mode: Mixed. Commands below are Ran evidence; schema, documentation,
workflow, and scope review are Static evidence. No production system, external
artifact, database, or real release membership was accessed.

## Delivered schema inventory

All schemas use Draft 2020-12 and stable version-1 identifiers:

1. `artifact-reference.schema.json`
2. `batch-member-index.schema.json`
3. `compatibility-envelope.schema.json`
4. `release-manifest.schema.json`
5. `rhessys-capability-index.schema.json`
6. `transformation-lineage.schema.json`
7. `validation-report.schema.json`

The complete illustrative JSON fixture/schema corpus is 49,775 bytes. It
contains no raw data or production membership.

## Executed gates

The host Python did not already contain `jsonschema`; the initial validator
invocation stopped with `ModuleNotFoundError`. Validation then ran in the
throwaway virtual environment `/tmp/utility-watershed-db08-venv.1LxvP3` with
the same pinned dependency used by CI:

```text
python -m venv /tmp/utility-watershed-db08-venv.1LxvP3
python -m pip install jsonschema==4.23.0
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_release_schemas.py
{"invalid_cases": 9, "schemas": 7, "status": "passed", "valid_cases": 7}

PYTHONDONTWRITEBYTECODE=1 python -m unittest scripts.tests.test_validate_release_schemas
.......
Ran 7 tests
OK
```

Additional Ran gates:

```text
python -m json.tool <every schema, case manifest, and fixture>
passed

python -m tabnanny scripts/validate_release_schemas.py scripts/tests/test_validate_release_schemas.py
passed

ruff check --no-cache scripts/validate_release_schemas.py scripts/tests/test_validate_release_schemas.py
All checks passed!

ruby -e "require 'yaml'; YAML.load_file(...)"
workflow YAML syntax passed

git diff --check
passed
```

Python AST compilation also passed. Ruff ran from the throwaway environment.
PyYAML and Actionlint were not installed on the host; Ruby parsed the changed
workflow YAML, no server application code changed, and the reusable CI workflow
runs the executable validator/tests under Python 3.12.

## Positive and negative coverage

The valid suite covers every schema exactly once and cross-checks the release
collection key, exact member count, ordered watershed keys, and member index.
The negative suite proves rejection of:

- duplicate collection and watershed identities;
- wildcard and target-overlapping removals;
- missing immutable verification assertion;
- precomputed RHESSys mode without a GeoTIFF;
- incompatible data contract version;
- credential-bearing HTTPS user information; and
- raw authentication token instead of `secret_ref`.

The test suite additionally mutates fixture coverage, release/index ordering,
collection and run identity, secret keys, and an expected-invalid version to
prove the harness itself fails closed.

## Static review

- `.github/workflows/data-contract-ci.yml` pins `jsonschema==4.23.0` and invokes
  the same validator and unit-test commands.
- `.github/workflows/deploy.yml` requires the reusable data-contract job before
  deployment; no workflow was dispatched.
- Relative documentation links and referenced repository paths were reviewed
  against the changed tree.
- A focused scan found no GitHub token, AWS access-key, or private-key pattern.
  Placeholder token/password strings exist only in named negative fixtures and
  are rejected by the suite.
- DB09 fingerprint/plan representation, DB10 provider selection, real releases,
  external fetches, database mutations, production access, and PR actions
  remain outside DB08. Commit and branch push were separately authorized after
  execution completed.
