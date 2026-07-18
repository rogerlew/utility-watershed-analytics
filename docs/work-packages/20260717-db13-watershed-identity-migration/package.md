# DB13 — Stable watershed identity migration

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB13`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-17. Authority covers repository changes and isolated forest1 database,
container, migration, compatibility, and rollback tests.

Post-close publication authorization: The operator explicitly authorized commit
and push on 2026-07-17 to
`origin/agent/database-backup-deployment-spec`; no pull request was authorized.

## Objective

Introduce a stable logical watershed identity without breaking current run-ID
reads: add collection, identity, and permanent run-alias records; backfill the
current domain rows; dual-link children; and expose stable-key API routes.

## Scope

Included:

- additive Django models and migrations for project-controlled collection and
  watershed identity plus permanent run-ID aliases;
- backfill of one logical identity and current alias for every existing
  watershed, with accepted exact standalone assignments only;
- nullable dual-compatible logical foreign keys on current watershed and child
  rows, including validation tooling for complete backfill;
- stable-key watershed, subcatchment, and channel API routes with stable child
  feature IDs;
- canonical `/watershed/key/<watershed_key>` browser routing, assigned legacy
  route redirects, and a narrow current-run context for existing analytics;
- historical run-ID alias resolution while preserving current run-ID response
  IDs and paths;
- production-shaped forward, compatibility, replacement, collision, reference,
  and bounded rollback tests in isolated forest1 PostGIS; and
- authoritative compatibility/rollback documentation, roadmap, catalog, and
  sanitized evidence.

Excluded:

- production or `wepp3` access or mutation;
- assignment of unreviewed batch-member watershed keys;
- destructive primary-key or old-child-FK removal, database-enforced child
  business-key constraints, release ledger, or reconciler;
- SBS/RHESSys stable-key API routing and production schema/application rollout
  owned by successor packages; and
- commit, push, or pull request.

## Authority and inputs

- DB06 evidence: `docs/database-domain-identity-audit.md`.
- DB07 contract: `docs/database-identity-metadata-contract.md`.
- DB08 schema contract: `docs/database-release-schema-contract.md`.
- Architecture: `docs/database-deployment-architecture.md` section 9.4.
- Starting revision: `ee9e70b54530300cea1b58e418436b3f35128856`.
- Production-shaped aggregate: 126 watersheds, 195,457 subcatchments, and
  86,895 channels with zero accepted-key duplicates or child orphans.

## Assumptions and decisions

- A generated UUID is the immutable internal database identity. The reviewed
  `watershed_key` is its nullable public logical key during expansion; it
  becomes mandatory only when all production assignments are reviewed.
- Existing `Watershed.runid` remains the serving primary key during the
  compatibility window. Additive links let old code read the expanded schema.
- The migration assigns only the four accepted collection keys and the exact
  Gate Creek and Mill Creek watershed keys. Batch member keys are not inferred.
- Run aliases are permanent mappings. A historical alias resolves to the
  identity's current serving revision; a retired identity returns 410 and an
  unknown identifier returns 404.
- Old run-ID endpoints retain their response IDs. New stable-key endpoints use
  stable watershed and child IDs.
- A legacy browser route redirects only when the API returns a reviewed stable
  key. The canonical route resolves the current source run once and provides it
  to unchanged analytics hooks.
- The later contract migration may make logical links non-null and remove old
  child revision foreign keys only after the dual-compatible rollout and
  reviewed complete key assignment.

## Plan

1. Add the identity models and expand/backfill migration.
2. Add alias resolution and stable-key API routes.
3. Add canonical browser routing and compatibility context.
4. Add migration, replacement, route, and rollback tests.
5. Run production-shaped isolated PostGIS validation.
6. Reconcile documentation, roadmap, catalog, and evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch: `agent/database-backup-deployment-spec`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository and isolated Docker/PostGIS on forest1
- Mutation boundary: DB13 code, migrations, tests, documentation, and disposable
  test databases/containers
- Production server and production database: not authorized

## Gates

- Django migration graph and `makemigrations --check` pass.
- Focused model, API, migration-executor, production-shaped, and rollback tests
  pass against isolated PostGIS.
- Old-code compatibility is proven at the expanded-schema point without relying
  on the new model fields.
- Run replacement preserves internal identity, child row IDs, stable child
  feature IDs, current run routes, and historical aliases.
- Duplicate watershed keys and duplicate aliases fail closed.
- A validation command rejects incomplete logical/alias/child backfill.
- Production image build, Ruff, full Django tests, documentation checks, secret
  scan, and `git diff --check` pass.
- Client lint, type check, production build, and full tests pass.

Skipped:

- production migration timing and rollout: DB27A requires separate production
  schema/application mutation authority;
- SBS and RHESSys stable-key API routes: their complete capability migration
  belongs to DB19A/DB25 and later compatibility rollout;
- contract removal of old links: unsafe before reviewed complete key assignment
  and the dual-compatible production rollout.

## Exit criteria

`EXECUTED-COMPLETE` requires the additive schema, complete existing-row
backfill, validation command, compatible old/new API behavior, replacement and
rollback proofs, production-shaped isolated execution, and reconciled durable
documentation.

Legitimate hold outcomes:

- `EXECUTED-HOLD-MIGRATION`: forward/backfill/rollback is not safe or bounded;
- `EXECUTED-HOLD-COMPATIBILITY`: old run-ID behavior or stable identity cannot
  be preserved at the documented compatibility point.

## Risks and recovery

- Risk: an inferred key silently merges unrelated watersheds.
  - Prevention: exact assignments only; batch keys remain null until reviewed.
- Risk: child rows remain linked only to a replaceable revision.
  - Prevention: backfill and validate a second logical FK without dropping the
    old compatibility FK.
- Risk: a historical run ID resolves ambiguously.
  - Prevention: the alias run ID is a primary key and one identity has at most
    one current serving revision.
- Risk: rollback discards stable identity records after new code has used them.
  - Recovery: rollback is supported only before identity-aware writes; after
    that boundary, roll forward with the additive schema.

## Artifacts

- `artifacts/db13-validation-evidence.md` — sanitized migration, compatibility,
  production-shaped, image, and validation evidence.

## Execution record

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| DB06/DB07/DB08 and current model/route review | repository at starting revision | Static | Additive UUID identity, nullable reviewed key, permanent alias, and dual child-link shape selected; no batch watershed key inferred. |
| `python manage.py test server.watershed.test_stable_identity server.watershed.test_stable_identity_migration` | final production image + disposable forest1 PostGIS | Ran | Twelve focused route, stable-feature-ID, collision, validation, expand/backfill, old-model, exact rollback, and closed-rollback-boundary tests passed. |
| `python scripts/accept_db13_migration.py` | production image + disposable `db13_accept` PostGIS | Ran | 126 watersheds, 195,457 subcatchments, and 86,895 channels migrated in 15.268 seconds and rolled back in 12.631 seconds; counts and child ID samples were unchanged. |
| `python manage.py test` | final production image + fresh disposable forest1 PostGIS | Ran | Full 127-test server suite passed after restoring the exact legacy unknown-detail 404 payload. |
| Client lint, type check, build, and `npm run test` | final client image / forest1 Docker | Ran | Canonical route tree and production build passed; lint/type checks passed; 40 files and 583 tests passed. |
| Production images | forest1 Docker | Ran | Final server image `sha256:7b003752...b7e17` and client image `sha256:09f1adc8...d68a5`; no DB13 container remained after validation. |
| Ruff and `makemigrations --check --dry-run` | final production image | Ran | Ruff passed and Django reported no model/migration drift; the no-database dry run emitted the expected unreachable-host history warning. |
| Python syntax, docs links/fences, secret-assignment scan, changed-file whitespace, and `git diff --check` | forest1/repository | Mixed | All applicable final gates passed. |

## Findings and deviations

- The first isolated focused run checked the Postgres container's local socket
  before network TCP was ready. The harness now gates on `pg_isready -h db` from
  the same Docker network; this was an environment readiness race, not a code
  failure.
- The initial reverse path left deferred FK trigger events pending before table
  removal. It now forces constraints immediate after deleting identity rows;
  actual forward/reverse migration tests and the production-shaped rehearsal
  pass.
- An early migration test reused a `MigrationExecutor` whose applied-state
  cache predated the forward migration. Reverse tests now instantiate a fresh
  executor and prove actual schema removal.
- The first full suite found that the new resolver changed the legacy unknown
  detail payload from `Not found.`. The exact old 404 body was restored and the
  complete suite passed.
- Final scope review caught that API aliases alone did not satisfy DB13's
  explicit redirect deliverable. The client now registers the canonical stable
  route, redirects assigned legacy routes, and keeps current source-run behavior
  through a narrow context; the full client gate passed.
- DB13 deliberately leaves batch-member stable keys unassigned and logical
  links nullable. Complete reviewed assignment and the destructive contract
  step remain later work; this is the documented compatibility boundary, not a
  partial execution result.

## Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria: met
- Blocker: none
- Successor: DB14 may add accepted watershed-domain integrity constraints.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or production row data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match recorded authority.
