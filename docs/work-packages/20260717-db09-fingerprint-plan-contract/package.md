# DB09 — Fingerprint and base-specific plan contract

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB09`

Evidence mode: Mixed

Execution authorization: The user authorized scaffold and execution on
2026-07-17, initially limited to repository changes and local validation on
`forest1`. The user separately authorized commit and push on 2026-07-17.
Production access or mutation and pull-request actions are not authorized.

## Objective

Define version-1 canonical semantic fingerprints for DB08 release subjects and
strict forward, exact-inverse, and empty-build plan contracts that fail closed
when the observed base differs from the reviewed base.

## Scope

Included:

- deterministic UTF-8 JSON canonicalization for a bounded scalar subset;
- versioned artifact, run, capability, watershed-domain, and release
  fingerprints;
- semantic normalizers that sort set-like collections by stable identity and
  omit only explicitly volatile or transport-only fields;
- a common deployment-plan schema plus forward, exact-inverse, and empty-build
  schema wrappers;
- explicit base/target manifest hashes, semantic fingerprints, migration and
  data/identity contracts, materializer digest/commit, and fingerprint version;
- exact per-watershed actions and expected row-count deltas;
- golden, order/format invariance, semantic-mutation, inverse, empty-build, and
  wrong-base replay proof; and
- reusable CI execution through the existing data-contract workflow.

Excluded:

- real release manifests or production plans;
- artifact-provider selection, upload, retention, or credentials (DB10);
- release-tool CLI/image work (DB11), database introspection/materialization,
  deployment, rollback execution, or production access; and
- geometry canonicalization from source coordinates: version 1 fingerprints
  only an already canonical CRS-qualified binary geometry digest.

## Frozen decisions

- `fingerprint_version` and `plan schema_version` are both `1`; unknown versions
  reject.
- Canonical bytes are UTF-8 JSON with NFC-normalized strings, lexicographically
  sorted object keys, no insignificant whitespace, lowercase JSON literals, and
  a final newline. Binary floating-point inputs are prohibited; JSON decimals
  are parsed exactly and encoded as normalized decimal strings.
- SHA-256 over canonical bytes is the fingerprint algorithm.
- Arrays remain ordered unless a subject normalizer explicitly treats them as
  sets. Artifact roles, aliases, collections, runs, capabilities, removals,
  lineage, and plan actions sort by their documented stable tuple.
- Artifact semantic identity includes content SHA-256, bytes, and media type;
  transport URI and `verified` assertion are validation inputs, not content.
- Release semantic identity excludes release ID, creation time, validation
  report location, authentication reference, and artifact transport URIs. It
  includes compatibility, exact membership, artifact content, removals,
  lineage, and materializer identity. The exact manifest SHA remains separately
  required in every populated plan state.
- A plan base is either the literal `EMPTY` state or a complete populated state
  reference. The target is always populated. Base matching is exact across all
  recorded fields; no wildcard, latest, or inferred base is valid.
- Exact inverse proof requires swapped base/target states, mirrored actions and
  negated deltas. Empty-build proof requires an `EMPTY` base and only additions.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch/commit: `agent/database-backup-deployment-spec` at
  `289aeb9b19f6eac69e6fec4bd1ef02d8622e9246`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: `origin/agent/database-backup-deployment-spec`
- Pull-request target: do not open a PR
- Authorized systems: repository and local `forest1` validation only
- Mutation boundary: DB09 schemas, fixtures, fingerprint/plan validator and
  tests, CI wiring, and authoritative documentation

## Gates

- `git diff --check` and exact changed-file review;
- all DB08 and DB09 schemas validate and all existing DB08 tests remain green;
- repeated-process and golden fingerprint bytes/hashes match exactly;
- irrelevant JSON formatting and set ordering do not change fingerprints;
- every covered semantic mutation changes its intended fingerprint;
- forward/inverse and empty-build relationships pass exact semantic checks;
- a mismatched observed base rejects before any action;
- plan schemas reject unknown versions, incomplete state coordinates, wildcard
  action identities, and incompatible contract/materializer coordinates;
- JSON, Python, workflow YAML, relative links, and secret-pattern checks pass;
  and
- no real release, production fact, credential, raw data, or bulky artifact is
  introduced.

Skipped gates:

- server/client suites: no application behavior changes;
- database clean-build/deployment/rollback: DB09 defines representation only;
- production and artifact-provider checks: no production or DB10 dependency.

## Exit criteria

`EXECUTED-COMPLETE` requires all five fingerprint subjects, all three plan
kinds, golden and negative proofs, CI integration, authoritative contract,
roadmap/catalog reconciliation, and compact evidence to pass.

Hold outcomes:

- `EXECUTED-HOLD-CANONICALIZATION`: an input type cannot be represented without
  an ambiguous scalar or ordering rule;
- `EXECUTED-HOLD-INVERSE`: a forward action lacks a deterministic inverse; or
- `EXECUTED-HOLD-BASE`: base coordinates do not prevent replay against a
  different state.

## Artifacts

- `artifacts/db09-validation-evidence.md`

## Execution record

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Package scaffold and DB08 handoff review | repository / `forest1` | Static | Scope, versions, canonical subset, semantic exclusions, plan coordinates, replay guard, gates, and holds frozen. |
| Golden fingerprint and semantic mutation suite | temporary Python 3.12 environment / `forest1` | Ran | Five subjects matched golden SHA-256 values; repeated process, exact decimal, Unicode, formatting, ordering, transport exclusions, and five intended mutations passed. |
| Plan schema and relationship validation | temporary Python 3.12 environment / `forest1` | Ran | Four schemas and three plans passed exact totals, forward/inverse mirroring, canonical forward hash, empty-build, and matching-base checks; wrong base rejected. |
| `python -m unittest scripts.tests.test_fingerprint_plan_contract` | temporary Python 3.12 environment / `forest1` | Ran | Twelve canonicalization, parser, replay, inverse, coordinate, and structural mutation tests passed. |
| Existing DB08 validator and tests | temporary Python 3.12 environment / `forest1` | Ran | Seven release schemas, seven valid fixtures, nine negatives, and seven tests remained green. |
| JSON, Ruff, Python, workflow YAML, link, fence, secret-pattern, and diff review | repository / `forest1` | Mixed | Applicable gates passed; Actionlint and host Ruff were unavailable, isolated Ruff passed, and no application code changed. |
| Publication authority review | repository / GitHub | Static | User authorized commit and push to the current origin branch on 2026-07-17; no PR or production action was requested. |

## Findings

- Semantic release identity and exact manifest-byte identity are separate and
  both required in populated plan states.
- The composed north run fingerprint matches its capability fingerprint, and
  the domain fixture matches both; disconnected composite subjects reject.
- A wrong observed base differing only in domain fingerprint rejects before any
  action. No deployment behavior was executed.
- Binary float objects reject; JSON decimal lexemes normalize exactly to
  version-1 decimal strings.

## Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: all fingerprint subjects, plan kinds, golden and
  negative proof, CI integration, and documentation reconciliation passed
- Successor: DB10 remains next; DB11 is now unblocked

## Closeout checklist

- [x] Status and evidence are accurate.
- [x] Applicable gates and skipped reasons are recorded.
- [x] Artifacts contain no secrets or prohibited data.
- [x] Authoritative contract and architecture are reconciled.
- [x] Catalog and roadmap are reconciled.
- [x] Commit, push, and PR actions match authorization.
