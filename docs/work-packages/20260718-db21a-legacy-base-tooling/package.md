# DB21A — Legacy-base export and adoption tooling

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB21A`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic production-shaped
fixtures, isolated Docker/PostGIS, and temporary content-addressed artifacts on
forest1. It excludes `wepp3`, actual production capture/adoption, real `/wc1`
production namespaces, commit, push, PR, and workflow dispatch.

## Objective

Create a source-independent canonical export of an unmanaged populated base,
prove DB20 can rebuild it exactly, and provide guarded adoption/rollback that
preserves all pre-existing domain and unrelated application rows.

## Decisions

- Reviewed identity assignment is an explicit, separate operation before
  export; adoption never assigns or rewrites domain rows.
- Exported ordinary artifacts use the DB20 metadata/GeoJSON/Parquet contract
  and content-addressed immutable storage, so there is no second rebuild writer.
- The baseline fingerprint includes the exact reviewed capability-bootstrap
  set even though those rows are inserted only inside adoption.
- Adoption creates the immutable DB15 ledger, exact bootstrap capabilities,
  attempt, and active pointer in one transaction after recomputing the reviewed
  fingerprint against locked serving rows.
- Rollback requires the exact baseline, removes only its bootstrap capability
  rows, restores coherent `EMPTY`, and retains immutable ledger/audit history.

## Plan

1. Freeze baseline/export shapes.
2. Add reviewed identity assignment.
3. Export DB20-compatible immutable artifacts.
4. Add guarded adoption and rollback.
5. Prove offline rebuild and mismatches.
6. Run gates and reconcile docs.

## Gates

- `git diff --check`.
- Final production server image, Ruff, and migration drift.
- Focused DB21A/DB20/DB21 tests and complete server suite.
- Export then rebuild from only exported artifacts to the same fingerprints.
- Adoption/rollback preserve exact domain and unrelated row snapshots.
- Wrong state, membership, migration, checksum, fingerprint, and capability
  bootstrap fail atomically.
- Documentation, links, secrets, scope, and disposable-resource cleanup.

## Exit criteria

`EXECUTED-COMPLETE` requires canonical content-addressed export, explicit
reviewed identity assignment, exact offline DB20 rebuild, guarded atomic
adoption, exact rollback to `EMPTY`, negative no-mutation proof, and reconciled
contracts/catalog/roadmap.

## Execution record

- Added exact reviewed identity assignment with atomic conflict/membership
  rejection.
- Added deterministic DB20-compatible metadata/GeoJSON/Parquet export,
  reserved exact EWKB replay, content-addressed manifest/objects, capability
  indexes, and runtime assets.
- Added durable manifest reload, immutable baseline-ledger installation, and
  materialization-member reconstruction for source-independent DB20/DB21 builds.
- Added guarded adoption and rollback APIs plus Django management commands.
  Adoption changes only ledger/attempt/pointer/bootstrap capability state;
  rollback removes only the exact bootstrap and restores `EMPTY`.
- Passed 15 focused DB20/DB21/DB21A tests and all 188 server tests in the final
  production image against disposable PostGIS on forest1.
- Used synthetic rows/artifacts only; no `wepp3`, real `/wc1` namespace,
  production mutation, commit, push, PR, or workflow dispatch occurred.

### Commands and evidence

| Gate | Result |
| --- | --- |
| Final production image build | Passed; `sha256:f17237f...` |
| Ruff and migration drift | Passed; no changes detected |
| Focused DB20/DB21/DB21A tests | 15 passed in 17.643 seconds |
| Full server suite | 188 passed in 62.974 seconds |
| Offline export/rebuild equality | Exact rows and both fingerprints matched |
| Adoption/rollback snapshots | Domain and unrelated rows unchanged |

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met
- Blocker: none
- First follow-on action: scaffold DB22 base-aware planner and exact inverse
- Successor package: DB22, not yet scaffolded

## Artifacts

- `artifacts/db21a-validation-evidence.md`
- `docs/database-legacy-base-adoption-contract.md`

## Closeout checklist

- [x] Package status/evidence mode are accurate.
- [x] Gates and skipped reasons are recorded.
- [x] Evidence contains no credentials, real artifact coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match authority.
