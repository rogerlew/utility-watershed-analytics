# DB30 — NASA successor and Bremerton locked inputs

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB30`

Evidence mode: Mixed

Execution authorization: On 2026-07-18 the operator requested execution of
DB30 and then identified
`wepp1:/geodata/wc1/batch/nasa-roses-202606-psbs/resources` as the missing NASA
source location. This authorizes bounded read-only access to the NASA and
Bremerton batch trees below `wepp1:/geodata/wc1/batch`, immutable publication
of accepted DB30 objects below
`forest1:/wc1/utility-watershed-analytics-artifacts/v1/production`, and the
repository authoring needed to lock and prove those inputs. It does not
authorize `wepp3`, source mutation on `wepp1`, database mutation, release
activation/adoption, public-serving changes, provider selection, deletion,
DB30A+, workflow dispatch, DB30 commit/push, or PR creation.

## Objective

Freeze the exact 93-member NASA successor and approved three-member Bremerton ordinary
release inputs, enrich the NASA target through the DB18 `WWS_Code` contract,
publish all accepted bytes immutably to the operator-owned `/wc1` artifact
store, and prove source-independent replay plus DB21 data semantics.

## Scope

Included:

- exact reviewed membership, stable keys, source run IDs, display names, and
  aliases for `nasa-roses-202606-psbs` and `bremerton-2026-psbs`;
- batch-master normalization from each BatchRunner's recorded, validated
  member template without changing source geometry or feature order;
- NASA metadata enrichment from the checksum-pinned public 395-feature WWS
  source through the implemented DB18 closed transform;
- boundary, subcatchment, channel, hillslope, soil, and land-use inputs for
  every accepted member;
- immutable publication, indexes, receipts, checksums, counts, exact Parquet
  joins, negative membership tests, private storage proof, and replay with all
  upstream reads disabled;
- small reviewed descriptors, indexes, receipts, and sanitized evidence in
  Git; bulky source and artifact bytes remain outside Git.

Excluded:

- `wepp3`, production database or application mutation, legacy-base adoption,
  release planning, activation, rollback, or public serving;
- Bremerton04, explicitly excluded by the operator after all five required
  child inputs were confirmed absent;
- Gate Creek, Victoria, Mill Creek, RHESSys capability work, paid/provider
  storage, source cleanup, and artifact-store garbage collection.

## Authority and inputs

- Roadmap: `docs/ROADMAP.md`, DB30.
- Inventory: `docs/database-inventory.md`, NASA enrichment and Bremerton rows.
- Preparation: `docs/database-source-preparation-contract.md`.
- Enrichment: `docs/database-nasa-202606-enrichment-contract.md`.
- Validation: DB21 and `docs/database-domain-identity-audit.md`.
- Starting repository revision: `a5a0616542c3258a6a17e2da3c4b63548cb07083`.
- Source roots: read-only
  `wepp1:/geodata/wc1/batch/nasa-roses-202606-psbs` and
  `wepp1:/geodata/wc1/batch/bremerton-2026-psbs`.
- Destination: new immutable objects only below
  `/wc1/utility-watershed-analytics-artifacts/v1/production` on `forest1`.

## Assumptions and decisions

- `forest1:/wc1` remains the binding operator-owned storage decision; DB30
  selects no provider.
- BatchRunner's persisted source resource, exact member template, validation
  summary, and run directories together are the source authority. The source
  GeoJSON files are not silently treated as completed masters when their
  properties contain historical or absent run IDs.
- Stable identities are explicit descriptor entries. BatchRunner templates are
  used only to bind source features to exact reviewed current run IDs.
- On 2026-07-18 the operator directed DB30 to leave out Bremerton04. Its source
  master feature remains checksum-locked and is named in the descriptor's
  explicit exclusion list; it produces no member or child request.
- Source coordinates remain mutable. Accepted receipt hashes and immutable
  destination objects, not URLs or source paths alone, are authority.
- The configured WEPPcloud JWT slots were tested without printing values and
  both are expired; DB30 therefore uses the authorized read-only `wepp1` source
  paths and records that transport deviation honestly.

## Plan

1. Freeze source metadata, membership, checksums, capacity, and destination.
2. Implement the narrow validated-master identity binding required by the real
   NASA and Bremerton resources, with failure tests.
3. Author exact descriptors and publish all accepted inputs immutably.
4. Validate geometry, counts, enrichment lineage, Parquet joins, and negative
   membership drift.
5. Replay from receipts with source reads forbidden.
6. Reconcile evidence, inventory, roadmap, catalog, and cleanup.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch/commit: `agent/database-backup-deployment-spec` at `a5a0616`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push DB30
- Pull-request target: do not open a PR
- Authorized systems: repository, bounded read-only `wepp1` DB30 source trees,
  public checksum-pinned enrichment read, and `forest1:/wc1`
- Mutation boundary: DB30 repository records and new immutable objects below
  `/wc1/utility-watershed-analytics-artifacts/v1/production`
- Executor/reviewer: Codex executes; `roger` owns authoritative dispatch

## Gates

- Correct source/destination hosts, at least 100 GiB free on `forest1:/wc1`,
  private production namespace, and no overwrite/deletion behavior.
- Exact 93-member NASA and approved three-member Bremerton source-feature/
  template/run-directory equality with unique explicit stable identities and
  exactly one reviewed Bremerton04 exclusion.
- All six ordinary roles exist for every member; GeoJSON/Parquet structure,
  geometry preservation, counts, exact Topaz joins, and checksums pass.
- NASA source checksum, join uniqueness, approved-field decisions,
  matched/unmatched counts, historical-run-ID exclusion, report, and lineage
  pass the DB18 contract.
- Generated DB08 indexes and all relevant semantic validators pass.
- Receipt-only replay performs zero source reads and reproduces exact index and
  receipt bytes.
- Accepted objects use mode `0600` below mode-`0700` directories and remain
  protected by the production retention contract.
- Focused and full release-tool tests, schema validation, secret scan,
  documentation-path review, and `git diff --check` pass.

Skipped:

- production database/application checks: DB30 neither accesses `wepp3` nor
  activates a release;
- public artifact-serving checks: DB30 locks local durable bytes; later
  explicitly authorized deployment work owns serving.

## Exit criteria

`EXECUTED-COMPLETE` requires exact locked and replayable ordinary inputs for
all 96 approved members, accepted NASA enrichment outputs and lineage, the
explicit Bremerton04 exclusion, immutable `/wc1`
publication, full real-data validation, reconciled authoritative records, and
no unauthorized production or public-serving action.

Legitimate holds include `EXECUTED-HOLD-MEMBERSHIP`,
`EXECUTED-HOLD-SOURCE`, `EXECUTED-HOLD-STORAGE`, and
`EXECUTED-HOLD-VALIDATION`.

## Risks and recovery

- Risk: source bytes or batch metadata change while freezing.
  - Prevention: record pre/post hashes and source revisions; stop on drift.
  - Recovery: retain accepted immutable objects and start a new reviewed
    source revision rather than overwrite.
- Risk: source identity normalization admits or remaps a feature.
  - Prevention: require an explicit feature-to-run mapping and exact set,
    uniqueness, order, and geometry tests; reject missing/extra/duplicate data.
  - Recovery: stop before index acceptance and correct the reviewed descriptor
    or source, never infer around the mismatch.

## Artifacts

- `artifacts/db30-validation-evidence.md`
- `data-releases/locked-inputs/db30/` — reviewed descriptors and generated
  indexes/receipts only; no bulky source data or credentials
- Local ignored administrative log under `docs/sys-administration/logs/`

## Execution record

| Gate | Evidence | Result |
| --- | --- | --- |
| Host, authority, capacity | `forest1`; bounded read-only `wepp1`; about 1.147 TB free | Passed; no `wepp3`, provider, database, activation, serving, or delete action |
| NASA membership/source | 93 members; 467 source records; 330,826,629 bytes | Passed; explicit keys and two former-run aliases per member |
| NASA index/replay | index `216dcd73...74fe`; receipt `1f129dc1...e3d3` | Passed; clean-cache replay made zero upstream calls and reproduced exact bytes |
| NASA enrichment | 93 matched, 0 target-unmatched, 302 source-unmatched, 0 duplicates | Passed; 93 historical run IDs ignored, geometry preserved, normalized target/output `75e65ee1...e2bb` |
| NASA semantics | 101,481 subcatchments, 42,523 channels, 279 exact Parquet joins | Passed; all 93 DB20 multipart geometry merges were valid |
| Bremerton decision | four-feature source master; Bremerton04 has 0/5 child files | Operator excluded Bremerton04; descriptor locks that exact exclusion |
| Bremerton index/replay | three members, 16 source records, 1,235,895 bytes; index `5e163527...b16f`; receipt `5958c385...78c8` | Passed; zero upstream calls and exact replay |
| Bremerton semantics | 321 subcatchments, 135 channels, nine exact Parquet joins | Passed; all three DB20 geometry merges were valid |
| Negative proof | missing, extra, duplicate, unlisted, and receipt-coordinate drift | Passed; all rejected before acceptance |
| Durable store | 1,047 objects, 4,343,444,249 bytes; inventory `e58f128e...ebf0` | Passed; every object hash/path, owner, file mode, and directory mode verified |
| Tests/builds | 66 release-tool, DB08/DB09, five focused and 209 full Django tests | Passed; one expected Django skip; final images `e24dd00d...cf3e` and `e38c037f...7e12` |

The source GeoJSON files do not themselves contain completed current run IDs:
NASA carries historical 2025 IDs and Bremerton carries no run IDs. DB30 added
one closed explicit source-property map plus reviewed exclusions; it is not a
general template engine. Real multipart child features also exposed that DB17
was counting raw geometry parts while DB20 staged them separately despite the
database business-key constraints. DB30 now counts materialized entities and
DB20 merges exact parts before Parquet joins. The full server suite proves no
regression.

The NASA target already contained every approved enrichment value. The fixed
join therefore produced an idempotent canonical target rather than changed
bytes. DB30 accepts that only after the same checksum, join, membership,
run-ID, geometry, field, lineage, and report checks pass; reuse of the broader
enrichment source remains fatal.

Pre-acceptance stops included expired configured JWTs, first-use SSH host-key
verification, resumable source transfers, a publication attempt that ended
before index emission, the synthetic-only non-idempotence rule, and raw
multipart feature counts. Each was corrected or rerun at the narrowest safe
boundary. Superseded immutable objects remain retained because DB30 has no
delete authority.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
