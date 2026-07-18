# DB10A — Forest1 artifact backup acceptance

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB10A`

Evidence mode: Ran

Execution authorization: The operator explicitly authorized continued DB10A
execution with `forest1:/wc1` as the backup infrastructure.

## Objective

Provision and accept the real forest1 artifact backup path with the smallest
practical single-operator control set: private files, content hashes, no
overwrite, enough capacity, and a tested restore.

## Scope

Included:

- `/wc1/utility-watershed-analytics-artifacts/v1`;
- private `test` and `production` namespaces;
- three deterministic test release fixtures;
- SHA-256 copy, inventory, repeat verification, and clean restore;
- partial copy, collision, corruption, missing-object, unavailable-path, and
  capacity proof;
- repository tool, tests, CI, documentation, and sanitized evidence.

Excluded:

- paid providers, cloud services, accounts, credentials, encryption services,
  webhooks, IAM-style roles, or billing;
- real production release artifacts;
- changes inside `/wc1/utility-watershed-analytics-db-backups`;
- ZFS dataset or snapshot administration requiring sudo; and
- commit, push, pull request, or production-server access.

## Authority and inputs

- Operator decision: use `forest1:/wc1`; do not circumvent it.
- Contract: `docs/database-artifact-store-contract.md`.
- Policy: `data-releases/storage-contract/v1/artifact-store-policy.json`.
- Starting revision: `245f328ba5e9e1eec05948a08990f9ccf00a5029`.
- Host: `forest1`; `/wc1` is ZFS with about 1.1 TB free at acceptance.

## Plan

1. Correct DB10 to the forest1 decision.
2. Add a standard-library acceptance tool.
3. Test it in an isolated temporary root.
4. Provision and exercise the real `/wc1` root.
5. Record sanitized results and reconcile the roadmap.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository and forest1 `/wc1`
- Mutation boundary: repository DB10/DB10A artifacts and
  `/wc1/utility-watershed-analytics-artifacts/v1`
- Production server: not accessed

## Gates

- DB10 contract validator and ten mutation tests;
- four isolated acceptance-tool tests, including idempotent rerun;
- real forest1 provision, backup, negative proof, and clean restore;
- private owner/mode and free-space observations;
- database backup path unchanged and separate;
- Python syntax, Ruff when available, `git diff --check`, documentation links,
  code fences, and secret-pattern review.

Skipped:

- provider, credential, encryption-service, cross-role, and alert-delivery tests:
  explicitly removed by the operator-authorized single-host design;
- ZFS snapshot proof: no noninteractive sudo and not required for this simple
  version;
- application/database suites: no application or database behavior changed.

## Exit criteria

`EXECUTED-COMPLETE` requires the real path, two private namespaces, three test
release backups, exact restore, all negative checks, at least 100 GiB free, an
idempotent rerun, and reconciled authoritative documentation.

## Risks and recovery

- Risk: forest1 and `/wc1` are one failure domain.
  - Response: keep source data until backup verification succeeds; revisit a
    second copy only if the operator later authorizes it.
- Risk: the single operator can delete files.
  - Response: no automated deletion, deterministic inventory, and tested clean
    restore. Host-level privileged compromise is accepted residual risk.
- Risk: fixture objects are mistaken for production.
  - Response: fixtures exist only under `test`; `production/releases` is empty.

## Artifacts

- `artifacts/db10a-forest1-acceptance.md` — sanitized observed results.

## Execution record

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| `df -hT /wc1`, `findmnt -T /wc1`, `zfs list` | forest1 | Ran | `/wc1` is writable ZFS; about 1.1 TB free; no sudo required for the authorized directory. |
| DB10 validator plus contract/acceptance unit tests | forest1 | Ran | Validator and all 14 focused tests passed. |
| `python3 scripts/accept_artifact_backup.py --root /wc1/utility-watershed-analytics-artifacts/v1` | forest1 | Ran | Three releases/objects copied; five negative cases passed; clean restore inventory matched exactly. |
| Identical real-path rerun | forest1 | Ran | Same inventory and restore SHA-256; accepted bytes were unchanged. |
| DB08, DB09, DB10, syntax, Ruff, YAML, docs, secret-pattern, and diff gates | forest1 / temporary validation environment | Mixed | All applicable gates passed; the first broad run lacked `jsonschema`, then the exact CI dependency was installed outside the repository and the full rerun passed. |
| Real tree mode/owner review | forest1 | Ran | All accepted directories are `0700`, files `0600`, owner `roger:roger`; production release directory is empty. |
| Database backup boundary review | forest1 | Ran | `/wc1/utility-watershed-analytics-db-backups` remains separate at `0700`; no contents were inspected or changed. |

## Findings and deviations

- The prior provider design was unnecessary and unauthorized; DB10 was amended
  to the binding forest1 decision before DB10A execution.
- `/wc1` has enough current capacity but is already 80% used; the 100 GiB
  preflight provides a simple fail-closed floor.
- This acceptance proves a local backup and restore, not independent-site
  disaster recovery.

## Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria: met
- Blocker: none
- Successor: DB11 release-tool foundation

## Closeout checklist

- [x] Status and evidence mode are accurate.
- [x] Applicable gates and skipped gates are recorded.
- [x] Evidence contains no secrets or large data.
- [x] Authoritative documentation reflects the operator decision.
- [x] Work-package catalog and roadmap are reconciled.
- [x] No commit, push, PR, provider, or production action occurred.
