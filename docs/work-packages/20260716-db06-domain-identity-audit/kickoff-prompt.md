# Kickoff prompt — DB06 domain ownership and identity audit

Execute
`docs/work-packages/20260716-db06-domain-identity-audit/package.md` to its
honest terminal state.

Repository: `/workdir/utility-watershed-analytics`

Starting branch or commit: `agent/database-backup-deployment-spec` at
`5931ca1058881a532678e053794f1509e4d40434`

Working branch: `agent/database-backup-deployment-spec`

Push target: do not push

Pull-request target: do not open a PR

Authorized systems: repository working tree, running development containers,
and disposable test databases on `forest1`

Mutation boundary: repository files plus disposable local reports/test data;
do not mutate existing application data, unrelated containers, host services,
or any production system

Read first: `AGENTS.md`, `docs/work-packages/README.md`, `docs/ROADMAP.md`, the
package, `docs/database-deployment-architecture.md`, and
`docs/wave-0-readiness.md`.

Produce the authoritative current-domain audit and deterministic read-only
proof command/tests described by the package. Trace schema, loaders, Parquet
joins, API routes, and client consumers. Do not choose DB07 identities or infer
production facts from empty development data. Run every applicable gate,
preserve sanitized evidence, and terminalize as complete or the specific
production-evidence, identity-ambiguity, or audit-defect hold.
