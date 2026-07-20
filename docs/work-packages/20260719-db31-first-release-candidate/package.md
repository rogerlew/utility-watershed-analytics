# DB31 — First target manifest and clean build

Status: `EXECUTED-COMPLETE`

Date: 2026-07-19

Roadmap item: `DB31`

Evidence mode: Mixed

Execution authorization: On 2026-07-19 the operator requested scaffolding and
execution of DB31. Authority covers repository changes, exact reads from the
accepted DB28–DB30 locked inputs and operator-owned forest1 artifact namespace,
deterministic publication of content-addressed DB31 target artifacts and
metadata below that same namespace, and disposable isolated PostGIS clean
builds on forest1. It excludes
wepp3 access or mutation, production activation/deployment, artifact deletion,
Mill Creek RHESSYS invention, Bremerton04, provider work, DB32, commit, push,
PR, and workflow dispatch.

## Objective

Produce the first complete desired-state release manifest, exact forward and
inverse plans bound to the active DB30A baseline, an independently keyed EMPTY
plan, and two fingerprint-identical clean builds without upstream access.

## Scope

Included:

- Gate Creek and all 31 accepted Victoria members;
- stable `mill-creek` identity with current WEPP run `some-oligopoly` and no
  RHESSYS capability;
- all 93 accepted `nasa-roses-202606-psbs` members replacing their legacy run
  IDs;
- Bremerton01–03 as three exact additions;
- only the accepted Gate Creek, Sooke09, and Sooke15 RHESSYS capabilities;
- exact accepted source member indexes and immutable object bytes, with
  deterministic Topaz ordering for target Parquet artifacts and child-derived
  target boundaries where required by the pinned materializer;
- deterministic manifest, source-validation report, forward plan, exact
  inverse, EMPTY-build plan, two independent clean-build reports, hashes, and
  aggregate evidence.

Excluded:

- Bremerton04, Mill Creek RHESSYS, inferred/empty/former-run capabilities, SBS,
  new source acquisition or enrichment, provider selection, object mutation or
  deletion, production reads/mutations, activation, DB32+, commit, push, PR,
  or workflow dispatch.

## Authority and inputs

- Governing roadmap: `docs/ROADMAP.md`, DB31.
- Contracts: `docs/database-clean-build-validation-contract.md`,
  `docs/database-base-aware-planner-contract.md`,
  `docs/database-fingerprint-plan-contract.md`, and
  `docs/database-release-schema-contract.md`.
- Starting revision: `cad3c035760b54312012e6d8f16bff8c211a7243`.
- Active base release: `2026-07-18.30`; manifest
  `bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5`.
- Accepted inputs: `data-releases/locked-inputs/db28/`, `db29/`, and `db30/`.
- Artifact root:
  `/wc1/utility-watershed-analytics-artifacts/v1/production` on forest1.
- Frozen target coordinates: `artifacts/reviewed-target.json`.

## Assumptions and decisions

- DB29's ordinary `some-oligopoly` result is accepted input despite DB29's
  RHESSYS-source hold. The hold is resolved by declaring no Mill Creek RHESSYS
  capability, not by substituting the former run or inventing an empty one.
- Bremerton04 remains excluded exactly as directed and locked by DB30.
- The target uses the baseline-compatible materializer coordinates already
  exercised by DB30A; DB31 does not change server code or schema. Source
  Parquet rows are uniquely keyed but generally unordered, so DB31 publishes
  deterministic PyArrow 22.0.0 copies sorted by Topaz identity and retains both
  source and target hashes in the validation report. All 129 accepted source
  boundaries fail strict child containment, and several materially disagree
  with child extents. DB31 therefore derives each target boundary as the GEOS
  3.13.1 convex hull of its accepted child geometries with a fixed `1e-9`
  degree robustness buffer, records old/new bounds and hashes, and preserves
  the original immutable inputs.
- No target stable watershed key is removed. Mill Creek and NASA are run/data
  replacements under their reviewed stable identities; Bremerton adds three.
- Every clean build reads content-addressed forest1 bytes directly and performs
  zero upstream fetches.

## Plan

1. Freeze exact membership, capabilities, coordinates, and hashes.
2. Validate and publish immutable DB31 metadata artifacts.
3. Build the target twice in independent disposable databases.
4. Compare fingerprints and generate bound plan bundle.
5. Validate schemas, negative boundaries, evidence, and cleanup.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics` on forest1.
- Starting branch: `agent/database-backup-deployment-spec` at `cad3c03`.
- Working branch: existing branch; do not create another branch.
- Push target: do not push.
- Pull-request target: do not open a PR.
- Authorized systems: forest1 repository, `/wc1` immutable artifact namespace,
  and disposable isolated Docker/PostGIS resources only.
- Mutation boundary: DB31 repository files, new content-addressed DB31 target
  objects and metadata, and disposable resources named for DB31.

## Gates

- Exact 129-member set with five collections, no duplicate stable key/run ID,
  three Bremerton additions, no removal, exact Mill/NASA replacements, and
  explicit Bremerton04 exclusion.
- Only Gate Creek, Sooke09, and Sooke15 declare RHESSYS; every capability index
  and referenced object is checksum/size/media exact.
- All ordinary indexes and all referenced objects match accepted receipt and
  artifact coordinates without upstream access.
- Target manifest and all plan kinds pass DB08/DB09 schemas and semantics.
- Forward plan binds exact active DB30A manifest/fingerprint; exact inverse
  binds the canonical forward hash; EMPTY plan is independently derived.
- Two isolated clean builds use separate empty PostGIS containers and produce
  identical target domain/capability fingerprints and counts.
- Application list/member reads, removals, and representative materialized
  RHESSYS behavior pass inside each isolated target.
- Focused/full server tests, Ruff, JSON/schema validation, secret scan,
  `git diff --check`, and complete disposable cleanup pass.

Skipped gates:

- Production backup/activation: DB31 has no production mutation authority.
- Mill Creek RHESSYS: explicitly deferred; absence is the reviewed capability
  declaration.
- Bremerton04: explicitly excluded by the operator and DB30.

## Exit criteria

`EXECUTED-COMPLETE` requires exact retained target artifacts, two independent
fingerprint-identical clean builds, exact bound plans, complete validation, no
upstream reads, and cleanup. A mismatch, missing object, schema/geometry/API
failure, nondeterministic fingerprint, or plan/base mismatch is an
`EXECUTED-HOLD-<REASON>` with no production action.

## Risks and recovery

- Risk: a locked input or `/wc1` object differs.
  - Prevention: verify every receipt, reference, size, and SHA before staging.
  - Recovery: stop; do not rewrite or delete immutable objects.
- Risk: build output differs between empty databases.
  - Prevention: identical pinned image, input hashes, plan, and bounded order.
  - Recovery: retain sanitized comparison evidence and hold DB32.
- Risk: an excluded capability/member is accidentally included.
  - Prevention: exact positive and negative set assertions before manifest
    publication and again after materialization.
  - Recovery: reject the candidate and publish a new hash; never overwrite it.

## Artifacts

- `artifacts/reviewed-target.json`
- `artifacts/target-canonicalization.json`
- `artifacts/target-release-manifest.json`
- `artifacts/source-validation-report.json`
- `artifacts/plans/forward.json`
- `artifacts/plans/exact-inverse.json`
- `artifacts/plans/empty-build.json`
- `artifacts/clean-build-1.json`
- `artifacts/clean-build-2.json`
- `artifacts/db31-validation-evidence.md`
- `artifacts/db31_operations.py`

Bulky immutable data and raw container/database output remain outside Git.

## Execution record

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Package scaffold and authority freeze | repository / forest1 | Static | Recorded before DB31 artifact publication or disposable database creation. |
| Exact source verification and deterministic target preparation | retained DB28–DB30 objects / forest1 | Ran | Verified 903 ordinary and 149 capability references with zero upstream fetches; published 346 ordered Parquets and 129 child-derived boundaries with complete source/target mapping. |
| Independent clean builds 1 and 2 | separate disposable PostGIS containers/volumes/networks | Ran | Both passed with domain `212ca78a...d386`, capability `4b41b7b2...44d4`, 129/110,270/46,296 serving counts, three capabilities, and identical semantic results. |
| Base-bound plan generation | isolated exact DB30A replay | Ran | Re-observed base domain `dab83d4c...8d57`; generated DB09-valid forward `086051b7...722d`, inverse `a57dad60...1112`, and EMPTY `822828e7...0974` plans. |
| Schemas, plan semantics, tests, Ruff, secrets, diff, publication, cleanup | pinned image / repository / forest1 | Mixed | 19 focused and 212 full server tests passed (one skipped); relevant Ruff, schema/semantic, secret, diff, immutable publication, and cleanup gates passed. |

### Findings and deviations

- Accepted source Parquets were uniquely keyed but generally unordered, so
  DB31 retained strict DB20 behavior and published 346 deterministic ordered
  target copies instead of weakening the materializer.
- Every accepted source boundary failed strict child containment. The reviewed
  child-derived convex-hull rule passed all 129 members and is retained with
  source/target bounds and hashes in `artifacts/target-canonicalization.json`.
- Early probes stopped honestly on readiness configuration, logical multipart
  counts, Parquet order, boundary containment, and the internal `testserver`
  host. No failed probe activated or retained serving state; each disposable
  environment was cleaned before the corrected retry.
- The first planner replay stopped because its harness omitted DB15's caller
  activation transaction. The corrected isolated replay re-observed the exact
  adopted base before producing any bound plan.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met
- Blocker, if held: none observed
- Successor package: DB32, only after separate dispatch

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match authorization.
