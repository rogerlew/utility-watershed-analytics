# DB29 — Mill Creek re-vendoring

Status: `EXECUTED-HOLD-RHESSYS-SOURCE`

Date: 2026-07-18

Roadmap item: `DB29`

Evidence mode: Mixed

Execution authorization: On 2026-07-18 the operator explicitly requested
commit and push of completed DB28, then scaffolding and execution of DB29. This
authorizes Codex to read the public `some-oligopoly` WEPPcloud run and public
Firewise Watersheds API, inspect operator-owned `forest1:/wc1`, publish new
immutable content-addressed DB29 objects below
`/wc1/utility-watershed-analytics-artifacts/v1/production`, and author the
bounded repository configuration, descriptors, indexes, receipts, evidence,
and contract updates required by DB29. It does not authorize `wepp3`, a
production data release, database mutation, release activation/adoption,
public-serving changes, provider selection, deletion, DB30+, DB29 commit/push,
PR creation, or workflow dispatch.

## Objective

Lock every ordinary input for successor Mill Creek run `some-oligopoly`,
re-vendor its actual precomputed RHESSys map assets to operator-owned durable
storage, build exact immutable indexes, and preserve stable `mill-creek`
identity plus explicit lineage from `mdobre-invincible-scarab` without relying
on the deleted source.

## Scope

Included:

- exact successor project directory and six ordinary source roles;
- successor loader/client/development references and stable-key lineage;
- every observed registered precomputed RHESSys scenario/variable map;
- immutable `/wc1` publication, exact indexes/receipts, structural validation,
  counts/joins, real reads, source-independent replay, private modes, capacity,
  and retention proof;
- honest source hold if no complete RHESSys source exists.

Excluded:

- recovering or reading the deleted former run as release authority;
- production database/application changes, release materialization, activation,
  adoption, former-row removal, public artifact serving, providers, or deletes;
- Gate, Victoria, NASA, Bremerton, DB30+, workflow, PR, commit, and push work.

## Authority and inputs

- Roadmap and acceptance criteria: `docs/ROADMAP.md` and
  `docs/database-inventory.md`.
- Stable identity: `docs/database-identity-metadata-contract.md` and
  `docs/database-watershed-identity-migration.md`.
- Ordinary preparation: `docs/database-source-preparation-contract.md`.
- RHESSys preparation: `docs/database-rhessys-artifact-tooling-contract.md`.
- Artifact store/client: `docs/database-artifact-store-contract.md` and
  `docs/database-artifact-client-contract.md`.
- Starting revision: `0b7021c` on
  `agent/database-backup-deployment-spec`.
- Successor run: public `some-oligopoly`.
- Former lineage alias: `mdobre-invincible-scarab`; never a fallback source.

## Plan

1. Freeze successor project coordinate and source inventory.
2. Lock and publish all six ordinary input roles.
3. Discover and close the RHESSys scenario/variable matrix.
4. Publish accepted maps and immutable capability index.
5. Validate joins, reads, replay, modes, and retention.
6. Reconcile application references, inventory, roadmap, and evidence.

## Gates

- Correct host, at least 100 GiB free, private production namespace, and no
  overwrite/delete behavior.
- Exact successor project directory and all six ordinary roles respond without
  credentials and pass DB17 structure/count/join validation.
- RHESSys source contains at least one complete reviewed scenario and every
  registered variable claimed by its catalog. Missing, protected, inferred, or
  mixed-revision maps are fatal to completion.
- Every accepted map passes TIFF metadata and real-pixel reads; catalog coverage
  is exact and receipt replay requires no upstream access.
- Stable `mill-creek` identity retains the former run as lineage/alias while
  ordinary and capability sources name only `some-oligopoly`.
- Full focused tests, schemas, fingerprints, secret scan, and
  `git diff --check` pass.

Skipped:

- production load/switch/removal and public catalog/tile activation: those
  require a later manifest, adoption, and production authority;
- former-source recovery: DB29 explicitly cannot rely on the deleted run.

## Exit criteria

`EXECUTED-COMPLETE` requires accepted ordinary and non-empty RHESSys locked
inputs for `some-oligopoly`, durable `/wc1` copies, exact replay, application
reference reconciliation, and all gates above. If ordinary inputs pass but no
authorized complete RHESSys source exists, close
`EXECUTED-HOLD-RHESSYS-SOURCE` with the ordinary artifacts retained and a
single concrete next action; do not invent, purchase, or silently omit maps.

## Execution record

| Gate | Evidence | Result |
| --- | --- | --- |
| Host, authority, and capacity | `forest1`; public/repository reads and new immutable `/wc1` objects only; about 1.1 TiB free | Passed; no `wepp3`, provider, database, activation, serving, or delete action |
| Exact successor coordinate | `some-oligopoly/disturbed9002_wbt` | Passed; all six ordinary roles respond publicly |
| Ordinary preparation | Six sources, 5,194,784 source bytes; member index `be3cdd7b...189d`; receipt `6c062a31...96d1` | Passed; one `mill-creek` member with former run retained only as alias |
| Ordinary semantics | 2,286 subcatchment features, 1,718 unique `TopazID` values, 4,245 channels, three exact Parquet joins | Passed |
| Source-independent replay | Clean cache with upstream fetch hard-failed | Zero upstream calls; exact index and receipt bytes reproduced |
| Artifact retention | Nine referenced objects, 5,199,550 bytes; production namespace now 372 objects | Hash/path, owner `roger`, and mode `0600` passed; private directories retained |
| RHESSys source | Successor browser has no `rhessys/`; 56 registered map coordinates probed; public successor catalog checked; operator-owned `/wc1` searched | Hold: 56/56 maps returned 404, catalog reports unavailable, and no local source exists |
| Tests and contracts | Full 61-test release-tool suite; DB08 schemas; DB09 fingerprints/plans | Passed |
| Cleanup | DB29 caches, probes, staging, and partial files | Passed; immutable accepted ordinary objects retained |

No RHESSys descriptor, empty capability, or inferred map matrix was published.
The former direct map coordinate returned HTTP 401 and was neither authorized
nor used; DB29 explicitly cannot rely on that source. Application-facing run
references remain unchanged because switching them before a successor
capability exists would violate the inventory order.

The single next action is to place or regenerate the complete reviewed Mill
Creek `rhessys/maps/<scenario>/<variable>.tif` tree under the successor run or
an operator-owned `/wc1` source path, then resume DB29 from the committed
ordinary descriptor/receipt. No provider or paid storage is needed.

## Artifacts

- `artifacts/db29-validation-evidence.md`
- `artifacts/mill-creek-rhessys-expected-files.txt` — 56-path deployed-registry
  checklist; explicitly not an observed source inventory
- `data-releases/locked-inputs/db29/`
- Local ignored administrative log under `docs/sys-administration/logs/`

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match authorization.
