# Kickoff prompt — DB14 watershed-domain integrity constraints

## Assignment

Execute
`docs/work-packages/20260717-db14-domain-integrity-constraints/package.md`
to its honest terminal state.

Repository: `/workdir/utility-watershed-analytics`

Starting commit: `907cd7e191da7a4501908653611caf273fb64527`

Working branch: `agent/database-backup-deployment-spec`

Push target: do not push

Pull-request target: do not open a PR

Authorized systems: repository and isolated Docker/PostGIS on forest1

Mutation boundary: DB14 code, migrations, tests, documentation, and disposable
test databases/containers; no production or `wepp3` access

## Read first, in order

1. `AGENTS.md`
2. `docs/work-packages/README.md`
3. `docs/ROADMAP.md`
4. `docs/work-packages/20260717-db14-domain-integrity-constraints/package.md`
5. `docs/database-domain-identity-audit.md`
6. `docs/database-identity-metadata-contract.md`
7. `docs/database-watershed-identity-migration.md`

## Required outcome

Implement and prove DB14's accepted database/model keys, exact analytical join
rejection, three-table rebuild ownership, cascade/protection behavior, and
production-shaped migration duration/lock evidence without closing DB13's
additive compatibility window.

## Execution constraints

- Preserve unrelated changes and stay within package scope.
- Never infer or require unreviewed batch-member watershed keys.
- Do not add normalized data tables merely to create new identities.
- Record only aggregate/synthetic evidence; never use production row values.
- Stop before production access, external mutation, push, or PR creation.
- Close honestly with the package's exact complete or hold state.

## Gates and closeout

Run the package's focused database/loader/migration tests, production-shaped
isolated rehearsal, full server CI commands, docs/secret/diff checks, and record
sanitized evidence. Reconcile the work-package catalog and roadmap.
