# Kickoff prompt — DB13 stable watershed identity migration

## Assignment

Execute
`docs/work-packages/20260717-db13-watershed-identity-migration/package.md`
to its honest terminal state.

Repository: `/workdir/utility-watershed-analytics`

Starting commit: `ee9e70b54530300cea1b58e418436b3f35128856`

Working branch: `agent/database-backup-deployment-spec`

Push target: do not push

Pull-request target: do not open a PR

Authorized systems: repository and isolated Docker/PostGIS on forest1

Mutation boundary: DB13 code, migrations, tests, documentation, and disposable
test databases/containers; no production or `wepp3` access

## Read first, in order

1. `AGENTS.md`
2. `docs/work-packages/README.md`
3. `docs/ROADMAP.md`
4. `docs/work-packages/20260717-db13-watershed-identity-migration/package.md`
5. `docs/database-domain-identity-audit.md`
6. `docs/database-identity-metadata-contract.md`
7. `docs/database-release-schema-contract.md`

## Required outcome

Implement and prove the additive stable-identity migration, complete existing
row backfill, permanent aliases, dual child links, stable-key API routes,
run-replacement identity preservation, old run-ID compatibility, and bounded
pre-write rollback. Do not infer batch member keys or perform production work.

## Execution constraints

- Preserve unrelated changes and stay within package scope.
- Keep `Watershed.runid` and old child foreign keys during compatibility.
- Assign only DB07's exact accepted keys; never derive identity from labels,
  geometry, utility metadata, HUC, or source suffix similarity.
- Label evidence Ran, Static, or Mixed and record the exact environment.
- Stop before production access, external mutation, push, or PR creation.
- Close as `EXECUTED-COMPLETE` only when every gate passes; otherwise use the
  package's exact hold state and first follow-on action.

## Gates and closeout

Run the package's focused migration and compatibility tests, production-shaped
isolated PostGIS rehearsal, current server CI commands, docs/secret/diff checks,
and record sanitized evidence. Reconcile the work-package catalog and roadmap.
