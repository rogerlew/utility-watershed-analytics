# DB28 — Gate Creek and Victoria locked release inputs

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB28`

Evidence mode: Mixed

Execution authorization: On 2026-07-18 the operator explicitly requested
scaffolding and execution of DB28 after authorizing DB27A commit and push. This
authorizes Codex to read the public Gate Creek and Victoria WEPPcloud sources,
use the existing Victoria copy on `forest1`, write immutable content-addressed
objects below `forest1:/wc1/utility-watershed-analytics-artifacts/v1/production`,
and author the reviewed descriptors, indexes, receipts, evidence, and contracts
needed to lock those inputs. It does not authorize `wepp3`, a production data
release, legacy-base adoption, database mutation, public serving changes,
provider selection, deletion of source data, DB29+, DB28 commit/push, PR
creation, or workflow dispatch.

## Objective

Freeze exact Gate Creek and 31-member Victoria ordinary build inputs, publish
them immutably to the operator-owned `/wc1` artifact store, and lock only the
observed Gate Creek dynamic RHESSys assets plus Sooke09/Sooke15 precomputed map
assets with exact indexes and source-independent replay proof.

## Scope

Included:

- exact reviewed Victoria membership and stable-key mapping;
- Gate Creek and Victoria boundary, subcatchment, channel, hillslope, soil, and
  land-use inputs required by the release builder;
- Gate Creek spatial-input GeoTIFFs and scenario/basin/hillslope/patch Parquets
  actually present for `S1`, `S2`, and `S4b`;
- Sooke09 and Sooke15 precomputed map GeoTIFFs actually present under reviewed
  scenarios and variables;
- immutable publication, indexes, receipts, checksums, structural validation,
  exact counts/joins, representative reads, replay without upstream access,
  private modes, capacity, and retention protection;
- repository descriptors and small generated indexes/receipts; bulky source
  and artifact bytes remain outside Git.

Excluded:

- capability inference for any other Victoria member;
- production activation, serving configuration, database changes, or release
  plans/manifests;
- Mill Creek, NASA, Bremerton, provider or paid storage work, and source
  cleanup or artifact-store garbage collection.

## Authority and inputs

- Inventory: `docs/database-inventory.md`, approved and RHESSys inventories.
- Architecture: `docs/database-deployment-architecture.md`, preparation and
  supported-case contracts.
- Ordinary source contract: `docs/database-source-preparation-contract.md`.
- RHESSys contract: `docs/database-rhessys-artifact-tooling-contract.md`.
- Artifact store/client contracts:
  `docs/database-artifact-store-contract.md` and
  `docs/database-artifact-client-contract.md`.
- Starting repository revision: `9512d05cd089f24727bb52d6fa120ea0f02dd81c`.
- Victoria local source root:
  `/wc1/batch/victoria-ca-2026-sbs`, observed with 32 run directories; the
  authoritative public inventory's exact 31-member set excludes local-only
  `Sooke05`.
- Gate Creek source: public run `aversive-forestry` at the exact configured
  `disturbed9002_wbt` coordinate.

## Assumptions and decisions

- `forest1:/wc1` is the binding storage decision. DB28 uses the existing
  production namespace and selects no provider.
- The stable Victoria member mapping is an explicit reviewed 31-entry list,
  not runtime suffix inference.
- Source coordinates may be public while source bytes remain mutable. Receipts
  and content-addressed destination objects, not URLs alone, are authority.
- The existing Victoria tree is a source, not the immutable destination.
- Capability is declared only for assets that pass exact structural and
  scenario/variable validation. Absence is not filled by inference.

## Plan

1. Freeze membership, source files, capacity, and destination state.
2. Author exact ordinary and RHESSys descriptors.
3. Publish every accepted input content-addressed to `/wc1`.
4. Validate structure, counts, joins, hashes, and representative reads.
5. Replay from receipts with upstream access forbidden.
6. Reconcile inventory, roadmap, catalog, evidence, and cleanup.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch/commit: `agent/database-backup-deployment-spec` at `9512d05`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push DB28
- Pull-request target: do not open a PR
- Authorized systems: repository, public WEPPcloud reads, and `forest1:/wc1`
- Mutation boundary: DB28 repository artifacts and immutable new objects below
  `/wc1/utility-watershed-analytics-artifacts/v1/production`
- Executor/reviewer: Codex executes; `roger` owns the authoritative dispatch

## Gates

- Correct host, at least 100 GiB free, private production namespace, and no
  overwrite/deletion behavior.
- Exact 31-member Victoria source/master/run-directory equality and explicit
  stable-key uniqueness.
- All six ordinary roles exist for Gate Creek and every Victoria member;
  GeoJSON/Parquet structure, member/count/join relationships, source/destination
  checksums, and representative reads pass.
- Gate dynamic scenarios and Sooke09/Sooke15 precomputed matrices are exact;
  TIFF/Parquet structure, geometry revision, variables, units, years, and
  representative data reads pass DB19/DB21 boundaries.
- Generated DB08 indexes and semantic cross-file checks pass.
- Receipt-only replay performs no upstream reads and reproduces exact bytes.
- Accepted objects are mode `0600` below mode-`0700` directories and are
  protected by the no-TTL/no-delete production retention contract.
- Focused release-tool tests, schema/fingerprint validation, documentation
  paths/links, secret scan, and `git diff --check` pass.

Skipped:

- production database/application tests: DB28 does not access or mutate
  `wepp3` or activate a release;
- public artifact-serving test: DB28 locks local durable bytes; serving is a
  later explicitly authorized deployment boundary.

## Exit criteria

`EXECUTED-COMPLETE` requires exact locked ordinary inputs for Gate Creek and all
31 Victoria members, exact accepted RHESSys assets for Gate/Sooke09/Sooke15
only, immutable `/wc1` publication, validated small indexes/receipts in Git,
source-independent replay, private retention, reconciled authoritative docs,
and no unauthorized production/publication action.

Legitimate holds include `EXECUTED-HOLD-MEMBERSHIP`,
`EXECUTED-HOLD-SOURCE`, `EXECUTED-HOLD-CAPABILITY`,
`EXECUTED-HOLD-STORAGE`, and `EXECUTED-HOLD-VALIDATION`.

## Risks and recovery

- Risk: mutable upstream bytes change during preparation.
  - Prevention: stream once, checksum, content-address, fetch back, and replay
    only from the accepted destination.
  - Recovery: stop; retain prior accepted objects and author a new source
    revision rather than overwrite.
- Risk: copying the full run trees captures unrelated transient files.
  - Prevention: publish only the six reviewed ordinary roles and exact RHESSys
    assets named by closed descriptors.
  - Recovery: orphaned content-addressed objects remain harmless and retained;
    DB28 has no delete authority.

## Artifacts

- `artifacts/db28-validation-evidence.md`
- `data-releases/locked-inputs/db28/` — reviewed descriptors and generated
  indexes/receipts only; no bulky source data or credentials
- Local ignored administrative log under `docs/sys-administration/logs/`

## Execution record

| Gate | Evidence | Result |
| --- | --- | --- |
| Host, authority, and capacity | `forest1`; repository/public reads plus new immutable `/wc1` objects only; about 1.1 TiB free | Passed; no `wepp3`, provider, database, activation, or serving action |
| Exact membership | Public inventory response SHA-256 `2e5a5890...4017`; reviewed member index SHA-256 `fa34c9c...a37` | Passed with 31 members; local-only `Sooke05` excluded |
| Ordinary inputs | 162 source records; 32 members; 11,903 subcatchment features; 14,721 channels; 96 exact Parquet joins | Passed |
| RHESSys inputs | Gate: 32 spatial rasters, 18 Parquets, three geometries; Sooke09: 56 maps; Sooke15: 40 maps | Passed after correcting yearly support and S4b geometry association |
| Schemas and semantics | Five real indexes plus seven valid/nine invalid fixtures | Passed |
| Source-independent replay | Five accepted receipts with upstream fetches hard-failed | Zero upstream calls; exact index and receipt bytes reproduced |
| Durable store | 363 objects, 4,002,489,915 bytes, inventory SHA-256 `da89a5dc...a71c` | Every object hash/path, owner, file mode, and directory mode passed |
| Tests and image | Full 61-test release-tool suite, including 23 focused tests; two no-cache normalized builds | Passed; reproducible audited image `sha256:fa7ed8fe...3ced` |
| Cleanup | Frozen staging, partial files, and disposable caches | Staging/partials absent; caches removed after replay |

Four legacy Gate rasters carry a `-32768` nodata TIFF tag recognized by the
DB19 parser but not exposed by GDAL's nodata API. All four still opened and
returned representative pixels with exact dimensions, bounds, CRS, and bands.
This compatibility fact is recorded for activation review; it did not require
changing or inferring source bytes.

Several pre-acceptance attempts stopped honestly on an HTTP 401 public-master
coordinate, a projected boundary, real TIFF/Parquet variants missing from the
synthetic contract, an overstated yearly range, and the initial S4b geometry
association. The final accepted evidence records the retries and corrected
hashes. Immutable superseded generated objects remain retained because DB28
did not authorize deletion.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match authorization.
