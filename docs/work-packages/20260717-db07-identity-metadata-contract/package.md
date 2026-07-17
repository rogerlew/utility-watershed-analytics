# DB07 — Stable identity and metadata authority contract

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB07`

Evidence mode: Mixed

Execution authorization: The user authorized scaffold and execution on
2026-07-17. Authority is limited to repository changes and local validation on
`forest1`; production access or mutation, commit, push, and pull-request actions
were not authorized during execution. The user separately authorized commit
and push after DB07 reached `EXECUTED-COMPLETE`; no pull request was authorized.

## Objective

Freeze a small, deterministic version-1 contract for stable collection and
watershed identity, replaceable source revisions, child business keys,
lineage, route compatibility, and field-level metadata/geometry authority so
DB08 can define release schemas without reopening identity decisions.

## Scope

Included:

- define immutable project-controlled key syntax and initial key assignments;
- distinguish logical watershed identity, collection membership, source run
  revision, display metadata, geometry, and child identity;
- define replacement, move, split, merge, retirement, and key-reuse rules;
- define current-route compatibility and alias behavior without implementing
  routes or migrations;
- define field-by-field authority and null/conflict semantics for current
  NASA ROSES, Victoria, Gate Creek, and Mill Creek sources;
- add worked positive and rejected fixtures for every roadmap scenario; and
- add a bounded standard-library validator proving fixture completeness and
  deterministic decisions.

Excluded:

- database models, migrations, constraints, loader/reconciler behavior, API or
  client route changes;
- DB08 JSON Schemas, release manifests, member indexes, fingerprints, artifact
  storage, or production inventory adoption;
- assigning every production batch member key without a reviewed exact member
  index; and
- any access to `wepp3`, external source fetch, or data mutation.

## Authority and inputs

- Governing roadmap: `docs/ROADMAP.md`, Wave 1 DB07.
- Governing architecture: `docs/database-deployment-architecture.md`, sections
  5, 8–10, and 17.
- Current-state input: `docs/database-domain-identity-audit.md` and completed
  DB06 production evidence.
- Approved target inventory: `docs/database-inventory.md`.
- Starting repository revision:
  `518d3428c7d35e97b44e4c85a93cca7f10c56f4e`.
- Frozen external inputs: none.

## Assumptions and decisions

- Stable keys are lowercase, URL-safe project identifiers and never encode a
  replaceable WEPPcloud run ID.
- A reviewed mapping assigns a key once; normalization proposes candidates but
  never silently decides whether two source members are the same watershed.
- Collection membership may change without changing watershed identity.
- Split and merge successors receive new keys; retired keys are tombstoned and
  never reused.
- Missing authoritative values and conflicting authorities fail preparation;
  explicit null clears only fields whose contract allows null.
- DB07 specifies route compatibility behavior but leaves implementation and
  deprecation timing to later compatible schema/code rollout packages.

## Plan

1. Freeze naming, identity, lineage, and compatibility decisions.
2. Define collection-specific field and geometry authority.
3. Add complete worked and rejected fixtures with a validator.
4. Run documentation and fixture gates and reconcile DB08 inputs.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit:
  `agent/database-backup-deployment-spec` at
  `518d3428c7d35e97b44e4c85a93cca7f10c56f4e`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: agent branch and fork `main` under separate closeout authority
- Pull-request target: do not open a PR
- Authorized systems: repository working tree and local validation on `forest1`
- Mutation boundary: DB07 documentation, fixtures, and their bounded validator;
  no application, database, runtime, or external-system mutation
- Executor/reviewer: Codex authors and validates; `roger` owns later publication
  and any identity exceptions requiring business review

## Gates

Always:

- `git diff --check`;
- package diff reviewed against included and excluded scope;
- relative Markdown links and referenced paths checked; and
- fixture output contains no secrets, credentials, row payloads, or external
  mutable inputs.

Applicable:

- standard-library validator passes all accepted fixtures;
- validator rejects every conflict fixture for the recorded reason;
- fixture coverage includes retained, renamed, replaced, moved, split, merged,
  metadata-only, geometry-only, removed, and unresolved-conflict cases;
- current collection field-authority matrices cover every watershed model
  field and use only defined authority/null/conflict policies; and
- architecture, roadmap, authoritative contract, and package catalog agree.

Skipped gates and reasons:

- backend/client suites: DB07 changes no application behavior;
- database/data-release gates: DB07 defines a contract but creates no schema,
  release, artifact, or data mutation;
- production checks: production evidence was completed by DB06 and DB07 needs
  no new production fact.

## Exit criteria

`EXECUTED-COMPLETE` requires:

- all included identity, lineage, compatibility, and authority decisions are
  explicit and leave no DB08 schema ambiguity;
- positive and negative fixtures pass their expected decisions; and
- authoritative docs, roadmap, and catalog are reconciled.

Legitimate hold outcomes:

- `EXECUTED-HOLD-IDENTITY-DECISION`: two observed records cannot be safely
  classified as retained/replaced/split/merged; record both candidates and
  request one business decision.
- `EXECUTED-HOLD-AUTHORITY-GAP`: a model field lacks one accepted authority or
  null policy; name the field and source conflict.
- `EXECUTED-HOLD-VALIDATOR`: fixtures are incomplete or nondeterministic; fix
  the smallest contract/fixture mismatch before DB08.

## Risks and recovery

- Risk: source-derived names become permanent logical identity.
  - Prevention: keep immutable keys in a reviewed mapping independent of run ID.
  - Recovery: reject the candidate and add an explicit mapping decision.
- Risk: metadata merge silently preserves stale or conflicting values.
  - Prevention: one authority per field, required presence, explicit-null
    semantics, and fail-closed conflicts.
  - Recovery: stop preparation and correct the source or authority decision.
- Risk: DB07 grows into DB08 schema implementation.
  - Prevention: fixtures describe decisions only; DB08 owns formal schemas.
  - Recovery: move schema-specific work to DB08 without widening this package.

## Artifacts

- `artifacts/identity-contract-fixtures.json` — current collection assignments,
  field coverage, and worked accepted/rejected decisions.
- `artifacts/db07-validation-evidence.md` — commands, coverage, and results.

Do not store secrets, environment files, production row data, database dumps,
or large source artifacts in this package.

## Execution record

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Package scaffold and authority review | repository / `forest1` | Static | DB06 dependency, repository-only boundary, decisions, fixtures, gates, and hold outcomes frozen. |
| Models, loaders, routes, inventory, and architecture review | repository at `518d342...` | Static | Current collections, 24 watershed fields, child keys, run-ID coupling, source replacement, planned inventory, and DB08 boundary mapped. |
| Version-1 identity and metadata contract | repository | Static | Stable key syntax and assignments, replaceable run aliases, child identities, lineage, route compatibility, field authority/null/conflict matrix, and independent change channels frozen. |
| Fixture validator | `forest1` | Ran | Four collections and all 24 fields passed; nine accepted lifecycle scenarios and three rejected conflict scenarios resolved exactly as recorded. |
| Validator mutation tests and model coverage | `forest1` | Ran | Seven tests passed, including live `Watershed` model field coverage and negative key, authority, expectation, and split-key-reuse cases. |
| Syntax and documentation gates | `forest1` | Ran | JSON parse, Python compile, diff whitespace, relative links, stale-state scan, secret/prohibited-artifact scan, and generated-file cleanup passed. Ruff was unavailable and no image was built. |

### Findings and deviations

- Stable collection keys deliberately omit batch dates and source run IDs. The
  architecture's illustrative NASA key was changed from the source revision to
  `nasa-roses`.
- The NASA successor's first enrichment source lacks currently populated
  utility fields. DB07 requires those fields to be present with values or
  explicit null plus provenance; DB18/DB30 must resolve the actual source and
  may not silently retain or drop values.
- Exact batch-member key assignment remains with reviewed DB08 indexes and
  later locked inventory packages. DB07 provides candidate syntax and rejects
  automatic identity inference, so this is not a package hold.
- Indefinite referenced-alias retention is simpler and safer than a date-based
  redirect window for this small public service.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: identity, lineage, compatibility, child-key, and
  field-authority decisions are explicit; positive/negative fixtures and all
  applicable gates pass; DB08 is unblocked
- Blocker, if held: not applicable
- First follow-on action, if held: not applicable
- Successor package, if any: DB08

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
