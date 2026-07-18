# Kickoff prompt — DB20 strict empty-database materializer

## Assignment

Execute `docs/work-packages/20260718-db20-strict-empty-builder/package.md`
to its honest terminal state.

Repository: `/workdir/utility-watershed-analytics`

Starting branch or commit: `d778ec3a4fe95aba91fcef3946e4374f70f907a0`

Working branch: `agent/database-backup-deployment-spec`

Push target: do not push

Pull-request target: do not open a PR

Authorized systems: repository, isolated Docker on `forest1`, and disposable
test databases/containers

Mutation boundary: DB20 code, tests, documentation, synthetic fixtures, and
disposable isolated database state; no `wepp3` or real release/artifact state

## Read first, in order

1. `docs/work-packages/README.md`
2. `docs/ROADMAP.md`
3. `docs/work-packages/20260718-db20-strict-empty-builder/package.md`
4. `docs/database-deployment-architecture.md`
5. `docs/database-staging-recovery-contract.md`
6. `docs/database-release-ledger-contract.md`
7. `docs/database-capability-runtime-contract.md`

## Required outcome

Implement and prove the strict bounded-memory path from checksum-locked local
artifacts to canonical DB16 staging rows and then, only against an EMPTY base,
to exact serving watershed, child, and declared capability rows. Any required
input or apply error must leave the serving domain and active pointer unchanged.

## Execution constraints

- Use existing validated release, run-state, identity, lineage, and capability
  declarations as inputs; do not infer or invent reviewed coordinates.
- Keep file reads, GeoJSON iteration, Parquet reads, and database writes within
  an explicit batch bound.
- Do not activate, adopt, access production, or inspect real artifacts.
- Preserve unrelated changes and record evidence honestly as Ran or Static.
- Stop before any unapproved external mutation.

## Gates and closeout

Run every gate in `package.md`, save sanitized evidence, update the durable
materializer contract, reconcile the roadmap/catalog, and use
`EXECUTED-COMPLETE` only if all exit criteria pass. Do not commit, push, open a
pull request, or dispatch a workflow.
