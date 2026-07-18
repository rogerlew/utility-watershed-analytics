# Kickoff prompt — DB08 versioned release and index schemas

Execute
`docs/work-packages/20260717-db08-release-index-schemas/package.md` to an honest
terminal state.

Repository: `/workdir/utility-watershed-analytics`

Starting commit: `c9ab4c90d42817da6343557acb82add5e087c69e`

Working branch: `agent/database-backup-deployment-spec`

Push target: do not push

Pull-request target: do not open a PR

Authorized systems: repository and local `forest1` validation only

Read first:

1. `docs/work-packages/README.md`
2. `docs/ROADMAP.md`, DB08
3. `docs/database-identity-metadata-contract.md`
4. `docs/database-deployment-architecture.md`, sections 8 and 17
5. `docs/database-inventory.md`

Create the version-1 Draft 2020-12 schema suite, representative valid fixtures,
required negative cases, deterministic structural/semantic validator, tests,
and CI wiring described by the package. Keep references provider-neutral and
verified; allow secret references only. Do not implement DB09 plans or
fingerprints, DB10 infrastructure, application/database behavior, a real
release, external fetch, production operation, commit, push, or PR.

Run every package gate and reconcile authoritative docs, roadmap, and catalog.
Use `EXECUTED-COMPLETE` only when every valid case passes, every negative case
fails for its recorded reason, and CI invokes the same checks.
