# DB06 — Domain ownership and identity audit

Status: `EXECUTED-HOLD-PRODUCTION-EVIDENCE`

Date: 2026-07-16

Roadmap item: `DB06`

Evidence mode: Mixed

Execution authorization: User-authorized scaffold and execution on 2026-07-16,
limited to repository mutation and non-production read-only execution on
`forest1`. Production access and mutation are not authorized.

## Objective

Create a reviewable, executable map of the current watershed data domain before
DB07 chooses stable project-owned identities: table ownership, persistence and
deletion boundaries, foreign keys, public and source identifiers, batch/member
identity, Parquet joins, uniqueness, row counts, schema-signature inputs, and
API/client compatibility consumers.

## Scope

Included:

- inventory Django-managed and extension-managed tables and classify watershed
  domain, persistent application state, observability state, and infrastructure;
- trace database keys through models, migrations, loaders, serializers, views,
  routes, client API calls, and source artifact joins;
- add a read-only identity-audit command with deterministic machine-readable
  output and tests for every proposed current business key;
- execute static review, backend tests, and read-only queries against the
  development database on `forest1`;
- document ambiguities and production-data questions as blockers rather than
  selecting DB07 identities early.

Excluded:

- accessing or changing `wepp3`, its database, services, files, or credentials;
- choosing `collection_key`, `watershed_key`, route migration, lineage, or
  metadata precedence decisions owned by DB07;
- adding database constraints or migrations, changing loader behavior, or
  mutating application data;
- inspecting or committing large GeoJSON, Parquet, GeoTIFF, database dumps, or
  credentials;
- implementing DB07 or later schemas, release tooling, or artifact storage.

## Authority and inputs

- Governing roadmap: `docs/ROADMAP.md`, Wave 1, DB06.
- Governing specification: `docs/database-deployment-architecture.md`, sections
  2, 7–9, 12, 15, 19, and 23.
- Work-package governance: `docs/work-packages/README.md`.
- Starting repository revision:
  `5931ca1058881a532678e053794f1509e4d40434`.
- Observed development state: `docs/wave-0-readiness.md` and the running
  development PostGIS/Django subset on `forest1`.
- Frozen external inputs: none. Repository source and disposable test fixtures
  are sufficient for authorized evidence; production remains unavailable.

## Assumptions and decisions

- DB06 records current identity mechanics and evidence. It does not convert
  `runid`, TOPAZ IDs, or source batch names into future stable identities.
- A model declaration or serializer field is Static evidence; a test or
  read-only query is Ran evidence within its named fixture/database boundary.
- Empty development tables can prove query behavior and schema visibility but
  cannot prove production uniqueness, counts, or dirty-data absence.
- Production facts remain unknown unless separately authorized read-only
  evidence is later added; no SSH or remote database command is allowed here.
- Generated reports must be deterministic, secret-free, bounded, and contain
  counts/violations rather than row payloads.

## Plan

1. Map schema, loaders, routes, and client consumers.
2. Specify current ownership and identity contracts.
3. Implement deterministic read-only audit tooling and tests.
4. Run gates, record evidence, and reconcile roadmap/catalog.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit:
  `agent/database-backup-deployment-spec` at
  `5931ca1058881a532678e053794f1509e4d40434`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository working tree, running development containers,
  and disposable test databases on `forest1`
- Mutation boundary: repository files plus disposable local reports/test data;
  existing application data, unrelated containers, and host services must not
  change
- Executor and review assignments: Codex authors and validates; the operator
  owns any later production read-only authorization and DB07 decisions

Every derived kickoff prompt must preserve these coordinates and permissions.

## Gates

Always:

- `git diff --check`
- package diff reviewed against included and excluded scope
- documentation paths, links, code fences, and commands checked
- deterministic audit output checked for secrets and row payloads

Applicable:

- Ruff using the command in `.github/workflows/server-ci.yml`;
- targeted command/model tests followed by the complete Django test suite;
- `python manage.py check`;
- read-only audit execution against the `forest1` development database;
- source review of client TypeScript consumers and loader Parquet joins;
- compare migration constraints with model metadata and audit queries.

Skipped gate and reason:

- client lint/build/tests: no client behavior is intended to change; client
  source is inspected as a compatibility consumer;
- production row-count/uniqueness queries: production read-only access is not
  authorized;
- data-release gates: DB06 creates no release or data mutation.

## Exit criteria

`EXECUTED-COMPLETE` requires:

- an authoritative audit enumerates every in-scope table, ownership class,
  persistence/deletion boundary, foreign key, identifier, Parquet join,
  schema-signature input, and API/client compatibility consumer;
- every claimed current business key is backed by a test or read-only query;
- row counts and duplicate/orphan results are recorded for an accepted current
  dataset, with ambiguities made explicit rather than inferred;
- authoritative docs, roadmap, and catalog are reconciled.

Legitimate hold outcomes:

- `EXECUTED-HOLD-PRODUCTION-EVIDENCE`: repository audit and executable checks
  pass, but the empty development database cannot establish production counts,
  uniqueness, or dirty-data absence. First follow-on: authorize the documented
  bounded read-only audit against `wepp3` and attach its secret-free report.
- `EXECUTED-HOLD-IDENTITY-AMBIGUITY`: a proposed current key is contradicted by
  schema, fixtures, or accepted data. First follow-on: record the exact
  collisions and route the naming/lineage decision to DB07 without adding a
  premature constraint.
- `EXECUTED-HOLD-AUDIT-DEFECT`: the command or tests mutate data, leak row
  payloads, produce nondeterministic output, or miss an in-scope consumer. First
  follow-on: fix the smallest reproducible defect and rerun every audit gate.

## Risks and recovery

- Risk: the audit accidentally mutates the database.
  - Prevention: use Django metadata and aggregate read-only queries; tests assert
    query-only behavior; production is excluded.
  - Recovery or rollback: stop, discard disposable fixtures, and restore the
    repository implementation to query-only behavior before rerunning.
- Risk: observed source identifiers are mistaken for future stable identity.
  - Prevention: label source, database, route, and proposed-business keys
    separately; reserve future naming and lineage for DB07.
  - Recovery or rollback: remove the premature decision and record the
    ambiguity as a DB07 input.
- Risk: reports expose user or source records.
  - Prevention: output aggregate counts, key names, and violation counts only.
  - Recovery or rollback: delete the report, review query shape, and rerun with
    bounded aggregation.

## Artifacts

- `artifacts/forest1-domain-identity-evidence.md` — sanitized commands,
  versions, counts, constraint/consumer review, and gate results.

Do not store secrets, environment files, database dumps, row payloads, or large
source data in the package directory.

## Execution record

Fill this section during execution.

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Package scaffold and authority review | `forest1`, 2026-07-16 | Static | Authorized repository-only execution; production excluded. |
| Django models/migrations, loader, API, client, and architecture review | repository at starting revision plus DB06 changes | Static | Mapped 55-table ownership, current/source/public keys, cascade boundary, implicit collections, Parquet joins, schema-signature inputs, and compatibility consumers in `docs/database-domain-identity-audit.md`. |
| Aggregate PostgreSQL catalog and identity queries inside `BEGIN TRANSACTION READ ONLY` | `forest1` development PostgreSQL 17.5 | Ran | Enumerated 55 tables and exact counts; three domain tables are empty; PK/FK constraints matched source; child unique constraints are absent; zero duplicate/orphan groups cannot establish production cleanliness. |
| `python manage.py audit_domain_identity --fail-on-violations` | running development Django/PostGIS subset | Ran | Deterministic aggregate-only report passed with zero violations and explicit empty-data/missing-constraint warnings; secret/row-payload scan passed. |
| Targeted Ruff and `server.watershed.test_identity_audit` | development server container and disposable test database | Ran | Ruff passed; 4 tests passed, including duplicate detection and no DDL/DML assertion. |
| `manage.py check`, migration drift, complete test suite | development server container and disposable test database | Ran | System check passed, no migration changes, 110 tests passed. |
| Production image build and Ruff | `utility-watershed-analytics-server:db06` | Ran | Image `sha256:4ef239173320f1a59edc2d37e62f0ceda5821af106377efe0df50a010e294250` built; Ruff passed. |
| Production row counts and identity audit | `wepp3` | Static | Not run; production read-only access was not authorized. |

### Findings and deviations

- Only three tables are watershed release-domain state. Ten Django auth/admin/
  session/control tables are persistent, five Silk tables are observability,
  and 37 tables are PostGIS/TIGER/topology infrastructure.
- The application has no public user-account workflow, but `auth_user` contains
  one development operational account and remains persistent state.
- `runid` is simultaneously source revision, database PK, API/route identity,
  child FK, client route/cache key, and upstream capability path.
- Subcatchment and channel business keys are not database-enforced. Tests prove
  the audit detects collisions, but the empty development database cannot prove
  production uniqueness.
- Parquet enrichment joins only on `topazid` within `runid`; duplicate Parquet
  rows are not explicitly rejected by the current loader.
- An earlier architecture sentence claimed a production duplicate audit without
  linked evidence. DB06 corrected the architecture to leave production
  uniqueness unverified.

### Terminal disposition

- Final status: `EXECUTED-HOLD-PRODUCTION-EVIDENCE`
- Exit criteria disposition: ownership, identity, deletion, join, signature, and
  compatibility mapping is complete; deterministic read-only proof tooling and
  repository gates pass. Accepted current-dataset row counts, uniqueness, and
  dirty-data evidence are unmet.
- Blocker, if held: the authorized development database has zero domain rows and
  production read-only access was not authorized.
- First follow-on action, if held: authorize the aggregate-only
  `audit_domain_identity --fail-on-violations` command against `wepp3` and
  preserve its secret-free report summary.
- Successor package, if any: DB07 remains blocked until DB06's accepted
  non-empty current-data evidence is attached and this package completes.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
