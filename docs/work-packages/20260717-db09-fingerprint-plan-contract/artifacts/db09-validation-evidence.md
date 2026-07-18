# DB09 validation evidence

Date: 2026-07-17

Environment: `forest1`, repository `/workdir/utility-watershed-analytics`,
branch `agent/database-backup-deployment-spec`, starting revision
`289aeb9b19f6eac69e6fec4bd1ef02d8622e9246`

Evidence mode: Mixed. Commands are Ran evidence; contract, schema, workflow,
and scope reviews are Static. No production system, database, external
artifact, or real release was accessed.

## Delivered contract

- Five semantic subjects: artifact, run, capability, watershed domain, release.
- Four Draft 2020-12 schemas: common deployment plan plus forward,
  exact-inverse, and empty-build wrappers.
- Three illustrative plans with exact states, per-watershed actions, change
  channels, row deltas, and materializer/contract coordinates.
- Five locked golden hashes, exact composed run/domain links, one semantic
  mutation per subject, and transport/order/format invariance.
- Exact inverse mirroring and canonical forward-plan hash, additions-only empty
  build, matching observed base, and a one-field wrong-base rejection.

The DB09 schema/fixture JSON corpus is 18,082 bytes and contains no raw data or
production membership.

## Executed gates

The same temporary Python 3.12 environment used for DB08 supplied
`jsonschema==4.23.0` and Ruff:

```text
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_release_schemas.py
{"invalid_cases": 9, "schemas": 7, "status": "passed", "valid_cases": 7}

PYTHONDONTWRITEBYTECODE=1 python -m unittest scripts.tests.test_validate_release_schemas
.......
Ran 7 tests
OK

PYTHONDONTWRITEBYTECODE=1 python scripts/validate_fingerprint_plan_contract.py
{"fingerprint_subjects": 5, "plan_schemas": 4, "plans": 3, "semantic_mutations": 5, "status": "passed"}

PYTHONDONTWRITEBYTECODE=1 python -m unittest scripts.tests.test_fingerprint_plan_contract
............
Ran 12 tests
OK

ruff check --no-cache scripts/release_fingerprints.py scripts/validate_fingerprint_plan_contract.py scripts/tests/test_fingerprint_plan_contract.py
All checks passed!
```

Every repository JSON document passed `python -m json.tool`. Python tab checks,
Ruby workflow-YAML parsing, relative Markdown link/code-fence checks, focused
secret-pattern review, exact changed-path review, and `git diff --check` passed.
Actionlint and host-level Ruff were unavailable; Ruff ran from the isolated
environment. Server/client suites were not applicable.

## Golden fingerprints

| Subject | Version-1 SHA-256 |
| --- | --- |
| Artifact | `bd6c0af1d71b05e2edaf8d7f01cd8b7d76b2bfaff44d22c028942c6995d1828a` |
| Run | `5eccdea91114222750a1aa694f72dc16bbf2caa17034d5cb767fb30f1b1fc4e4` |
| Capability | `8305c713fbe77f300797360faae8ce95d6b5b9db1b45fab514bb233392496037` |
| Watershed domain | `82265988a19375d28782c9586d7cd1264f26b9c9314eb6f7ef8cfd07ffa935cd` |
| Release | `d0329e66195abce8c56ed050dea1cc9e4809ac42025fcdebb4496711ea777f59` |

The artifact CLI ran in two independent subprocesses and returned identical
golden output. Exact decimal formatting, object order, Unicode normalization,
declared set ordering, artifact transport URI, release ID/time, validation URI,
and authentication reference did not affect their subject where declared
irrelevant. Duplicate JSON keys and binary floats rejected. Each covered
semantic change altered its subject fingerprint.

## Boundary review

- Semantic release fingerprints supplement rather than replace exact manifest
  SHA-256 values in plan state.
- Base comparison is complete object equality and occurs before any future
  artifact fetch or staging.
- `EMPTY` is reconstruction proof only and never authorizes destructive reset.
- Fixtures use repeated illustrative digests and `example.test` locations.
- DB10 provider/storage work, DB11 CLI/image work, real plans, database actions,
  production access, and PR remain outside DB09. Commit and branch push were
  separately authorized after execution completed.
