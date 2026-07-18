# Kickoff prompt — DB21 clean-build reproducibility

Execute `docs/work-packages/20260718-db21-clean-build-reproducibility/package.md`
to its honest terminal state.

Repository: `/workdir/utility-watershed-analytics`

Starting branch/commit: `8eb707e`

Working branch: `agent/database-backup-deployment-spec`

Push target: do not push

Pull-request target: do not open a PR

Authorized systems: repository, isolated Docker on forest1, disposable
PostGIS/test databases, and generated temporary artifact directories

Mutation boundary: DB21 code/tests/workflow/docs and disposable state only; no
`wepp3`, real artifacts, production database, commit, push, PR, or dispatch

## Read first

1. `docs/work-packages/README.md`
2. `docs/ROADMAP.md`
3. `docs/work-packages/20260718-db21-clean-build-reproducibility/package.md`
4. `docs/database-fingerprint-plan-contract.md`
5. `docs/database-empty-materializer-contract.md`
6. `docs/database-capability-runtime-contract.md`

## Required outcome

Implement artifact, run/release staging, active database, and application
validators; bounded stable serving/capability fingerprints; sanitized reports;
and exact CI proof that two fresh DB20 builds from the same locked synthetic
release produce identical results. Exercise public GeoJSON and one
checksum-verified materialized RHESSys query. Fail negative releases before
acceptance.

## Constraints and closeout

- Preserve DB09 fingerprint version 1 and prove script/server parity.
- Reuse DB20 inputs, staging, and mutation semantics.
- Never turn required checks into warnings or fetch undeclared paths.
- Do not infer production, push, PR, or dispatch authority.
- Run every package gate, save sanitized evidence, reconcile contracts and the
  forward roadmap, and use an explicit hold if any required gate fails.
