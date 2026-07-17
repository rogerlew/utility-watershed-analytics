# Kickoff prompt — DB07 stable identity and metadata authority contract

Execute
`docs/work-packages/20260717-db07-identity-metadata-contract/package.md` to an
honest terminal state.

Repository: `/workdir/utility-watershed-analytics`

Starting commit: `518d3428c7d35e97b44e4c85a93cca7f10c56f4e`

Working branch: `agent/database-backup-deployment-spec`

Push target: do not push

Pull-request target: do not open a PR

Authorized systems: repository and local `forest1` validation only

Read first:

1. `docs/work-packages/README.md`
2. `docs/ROADMAP.md`, DB07
3. `docs/database-domain-identity-audit.md`
4. `docs/database-inventory.md`
5. `docs/database-deployment-architecture.md`, sections 5 and 8–10

Freeze the version-1 identity, lineage, route-compatibility, child-key, and
field-authority decisions. Add worked accepted and rejected fixtures covering
every DB07 scenario and a bounded validator that proves completeness and
deterministic resolution. Do not implement DB08 schemas, application code,
migrations, releases, external fetches, or production operations.

Run every package gate, reconcile the authoritative docs, roadmap, and catalog,
and use `EXECUTED-COMPLETE` only when DB08 has no remaining identity or metadata
authority decision to invent.
