# DB10 — Durable artifact backup contract

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB10`

Evidence mode: Mixed

Execution authorization: The operator authorized repository authoring and made
the authoritative decision to use `forest1:/wc1` rather than a paid provider.

## Objective

Freeze the simple, single-operator artifact backup contract required before
DB10A accepts the real forest1 path.

## Scope

Included:

- `forest1:/wc1/utility-watershed-analytics-artifacts/v1` storage root;
- separate private test and production directories;
- SHA-256 content-addressed copies with no overwrite;
- active plus two rollback retention and manual cleanup;
- capacity, integrity, failure, and restore rules;
- six public/public-sanitized artifact classes; and
- standard-library validation and tests.

Excluded:

- paid providers, cloud accounts, buckets, credentials, or external services;
- real production artifacts or production mutation;
- DB01 database backup changes; and
- DB11 release tooling or DB12 application cache implementation.

## Authority and inputs

- Governing roadmap: `docs/ROADMAP.md`, DB10 and DB10A.
- Authoritative contract: `docs/database-artifact-store-contract.md`.
- Machine policy: `data-releases/storage-contract/v1/`.
- Starting revision for the correction: `245f328ba5e9e1eec05948a08990f9ccf00a5029`.

## Decision correction

The first DB10 revision selected Backblaze B2 without operator authority. The
operator rejected that decision and reaffirmed existing forest1 infrastructure.
No provider account was accessed, created, contacted, or charged, and no data
left forest1. This package now records the operator decision as authoritative.

Repository specifications that conflicted with the decision were amended rather
than treating them as authority to expand infrastructure.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository and `forest1:/wc1`
- Mutation boundary: DB10/DB10A repository artifacts and the DB10A artifact
  backup root only

## Gates

- `python3 scripts/validate_artifact_store_contract.py`
- `python3 -m unittest scripts.tests.test_artifact_store_contract`
- `git diff --check`
- documentation path/link/code-fence review

Skipped:

- cloud/provider checks: explicitly outside the operator decision;
- application and database suites: no application or database behavior changed.

## Exit criteria

`EXECUTED-COMPLETE` requires the local contract, artifact-class and failure
coverage, fail-closed mutation tests, and explicit DB10A acceptance handoff.

## Execution record

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Operator decision reconciliation | conversation / repository | Mixed | Paid-provider choice superseded by authoritative forest1 decision; no external action occurred. |
| `python3 scripts/validate_artifact_store_contract.py` | forest1 | Ran | Two namespaces, one operator, six artifact classes, and seven failure cases passed. |
| `python3 -m unittest scripts.tests.test_artifact_store_contract` | forest1 | Ran | Ten fail-closed contract tests passed. |

## Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria: met by the corrected forest1 contract
- Successor: `../20260717-db10a-artifact-store-infrastructure/package.md`

## Closeout checklist

- [x] Status and evidence mode are accurate.
- [x] The authoritative operator decision is recorded.
- [x] No external provider claim remains authoritative.
- [x] Artifacts contain no secrets or large data.
- [x] Roadmap, architecture, catalog, policy, validator, and tests agree.
- [x] Commit and push remain unauthorized for this execution.
