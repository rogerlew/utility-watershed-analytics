# DB30A — Production legacy-base capture and adoption

Status: `EXECUTED-HOLD-PUBLIC-ARTIFACT-SERVING`

Date: 2026-07-18

Roadmap item: `DB30A`

Evidence mode: Mixed

Execution authorization: On 2026-07-18 the operator requested scaffolding and
execution of DB30A. This authorizes the bounded `wepp3` production reads and
release-metadata, reviewed identity, and capability-bootstrap mutations defined
here, after a fresh verified encrypted backup to `forest1:/wc1` and a complete
isolated rehearsal. It authorizes immutable legacy-baseline publication to the
operator-owned artifact store on `forest1`. It does not authorize changing or
deleting serving watershed/child rows, activating the DB31 target release,
inventing unavailable capabilities, provider selection, reboot, operating-
system changes, unrelated service/configuration changes, commit, push, PR, or
workflow dispatch.

On 2026-07-19 the operator separately authorized committing and pushing the
completed DB30A work and confirmed temporary passwordless sudo availability.
That publication authority does not widen DB30A into the DB30B public-artifact
serving configuration/deployment scope; no sudo action is needed for publication.

## Objective

Capture the exact populated production watershed base as source-independent
immutable artifacts, assign its reviewed stable identities, prove an exact
rebuild and adoption/rollback cycle on an isolated production-shaped restore,
then atomically register that unchanged base as the active legacy release.

## Scope

Included:

- exact current 126-member production membership, watershed/child rows,
  identities, aliases, counts, bounds, migrations, and fingerprints;
- stable identity assignment derived from the locked Gate Creek, Victoria,
  Mill Creek, and NASA successor mappings already reviewed in DB28–DB30;
- immutable DB20-compatible export, legacy manifest, ledger, rebuild report,
  and first-inverse source artifacts below
  `forest1:/wc1/utility-watershed-analytics-artifacts/v1/production`;
- capability bootstrap only for Gate Creek, Sooke09, and Sooke15 from the
  accepted DB28 indexes and immutable artifacts;
- fresh encrypted backup, isolated restore, fingerprint-equal rebuild,
  adoption, API/capability checks, rollback to `EMPTY`, fallback checks, and
  adoption again before production mutation;
- production adoption under the canonical exclusive host lock, with independent
  before/after domain and non-watershed fingerprints.

Excluded:

- any replacement/addition/removal in the serving watershed domain;
- Mill Creek RHESSys, because DB29 remains held without an accepted source;
- inferred or unverified SBS/capability assets, DB31 target preparation, DB32,
  DB33, deployment, schema/code rollout, reboot, provider, deletion, commit,
  push, PR, or workflow dispatch. The later publication authorization removes
  only the commit/push exclusions.

## Authority and inputs

- Governing roadmap: `docs/ROADMAP.md`, DB30A.
- Adoption contract: `docs/database-legacy-base-adoption-contract.md`.
- Production runbook: `docs/runbooks/production-runtime.md`.
- Backup runbook: `docs/runbooks/database-backup-restore.md`.
- Starting repository revision: `22647350b9163587485239af1c28e5430937af49`.
- Reviewed ordinary inputs: `data-releases/locked-inputs/db28/`, `db29/`, and
  `db30/`.
- Reviewed capability inputs: the three DB28 RHESSys indexes and receipts.
- Production: `wepp3`; development/backup/artifact host: `forest1`.

## Assumptions and decisions

- `forest1:/wc1` is the binding operator-owned backup/artifact destination; no
  provider decision is reopened.
- Production should still contain Gate Creek, former Mill Creek, 31 Victoria
  members, and 93 old NASA members with coherent `EMPTY` and migration `0011`.
  Any drift is a hold.
- Old NASA identities use the reviewed DB30 successor watershed keys while the
  old production run IDs remain current for this legacy baseline and successor
  run IDs remain aliases. Former and successor Mill Creek share `mill-creek`.
- Capability bootstrap is limited to Gate Creek, Sooke09, and Sooke15 because
  those are the only accepted durable capability indexes. No empty, inferred,
  provider-backed, or former Mill capability is substituted.
- Production adoption may create stable identity/alias rows, release ledger,
  release attempts, capability rows, and the active pointer. It may not change
  the values or membership of existing watershed, subcatchment, channel, auth,
  session, or unrelated application rows.

## Plan

1. Freeze production/runtime/backup/artifact and reviewed mapping coordinates.
2. Create and independently verify a fresh encrypted off-host backup.
3. Restore production into isolated PostGIS and assign reviewed identities.
4. Export, rebuild, adopt, verify, roll back, and adopt again in isolation.
5. Repeat reviewed identity assignment/export/adoption under the production lock.
6. Verify fingerprints/APIs/capabilities, reconcile evidence, and clean up.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch/commit: `agent/database-backup-deployment-spec` at `2264735`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: `origin/agent/database-backup-deployment-spec`
- Pull request: do not open
- Authorized systems: repository/forest1, bounded wepp3 production, encrypted
  backup repository, isolated forest1 PostGIS, and operator-owned artifact root
- Mutation boundary: reviewed identity/alias links, immutable baseline objects,
  release ledger/attempt/pointer, and three reviewed capability rows only
- Executor: Codex; approver and rollback owner: `roger`

## Gates

- Correct hosts, clean checkouts, canonical runtime/lock/database identity,
  migration `0011`, coherent `EMPTY`, no existing release ledger, and exact
  126/195,457/86,895 production counts.
- Fresh verified encrypted off-host backup independently visible on forest1
  before the first production database mutation.
- Reviewed mapping covers every current run exactly once with unique keys and
  complete current/successor alias sets.
- Isolated restored copy matches production, exact rebuild from exported
  artifacts matches the captured domain/capability fingerprints, and the full
  adopt/verify/rollback/verify/adopt cycle passes.
- All immutable objects match content paths, sizes, private permissions, and
  source-independent reads.
- Production before/after snapshots prove no serving watershed/child or non-
  watershed change beyond reviewed identity links and adoption metadata.
- Active release, manifest, migration, fingerprints, three RHESSys capability
  rows, public APIs, and runtime health agree after adoption.
- Focused/full server tests, Ruff, schema checks, secret scan, path review,
  `git diff --check`, and bounded cleanup pass.

Skipped:

- Mill Creek RHESSys and SBS activation: no accepted durable indexed source;
  DB30A must not invent capability authority.
- Target release planning/activation: DB31 and later packages own it.

## Exit criteria

`EXECUTED-COMPLETE` requires a fresh verified backup, exact reviewed identity
assignment, immutable source-independent baseline, fingerprint-equal isolated
rebuild and adoption/rollback/adoption rehearsal, active production legacy base
with unchanged serving/non-watershed rows, three accepted durable RHESSys
capabilities, complete validation, and cleanup.

Legitimate holds include `EXECUTED-HOLD-PREFLIGHT`, `-BACKUP`, `-IDENTITY`,
`-CAPABILITY`, `-REHEARSAL`, `-EXPORT`, `-ADOPTION`, `-VERIFICATION`, and
`-PUBLIC-ARTIFACT-SERVING`.

## Risks and recovery

- Risk: reviewed mapping or serving state differs.
  - Prevention: exact-set comparison and atomic assignment before export.
  - Recovery: stop; restore no data and correct the reviewed package.
- Risk: adoption verification fails.
  - Prevention: complete cycle on the exact restored copy first.
  - Recovery: invoke the exact rehearsed rollback to coherent `EMPTY`, verify
    fingerprints/fallback, and hold. The fresh encrypted backup remains the
    separate disaster-recovery boundary.

## Artifacts

- `artifacts/reviewed-identity-mapping.json`
- `artifacts/reviewed-adoption-plan.json`
- `artifacts/db30a_operations.py`
- `artifacts/db30a_production.sh`
- `artifacts/db30a_rollback.sh`
- `artifacts/db30a-validation-evidence.md`
- Content-addressed manifest and objects remain outside Git under `/wc1`.
- Local ignored administrative log under `docs/sys-administration/logs/`.

## Execution record

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Package scaffold and authority freeze | repository / forest1 | Static | Recorded before production access. |
| Fresh encrypted backup and independent check | wepp3 to forest1 | Mixed | Snapshot `301088aea8d9378b457478a71c29fe36df7c459cc2f6a04282fbf4e6685cf7ba`; backup-set SHA-256 `609c9118caee7590432e9b5f3c430e18751b4fd6005568d97fcac4d51880cbf4`; metadata and rotating `1/100` data check passed. |
| Exact isolated restore and export | forest1 | Mixed | Roles, memberships, schema, migrations, sequences, counts, and fingerprints matched; release `2026-07-18.30` exported with manifest `bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5`. |
| Source-independent rebuild and adoption cycle | forest1 | Mixed | Exact counts/fingerprints, API checks, adoption, rollback to `EMPTY`, fallback checks, and retained-ledger re-adoption passed. |
| Reviewed identity assignment, export, and adoption | wepp3 | Mixed | Exclusive lock held; 126 identities and 313 aliases matched review; serving rows and 57 unaffected tables remained unchanged; exact manifest activated. |
| Materialized capability/public object check | wepp3 / public endpoint | Mixed | Gate Creek materialized query failed closed because the declared artifact URI returned frontend HTML rather than the immutable object. |
| Rehearsed rollback and cleanup | wepp3 / forest1 | Mixed | Production returned to coherent `EMPTY`; Gate Creek fallback returned 173 rows; temporary containers, volumes, networks, credentials, and transferred cache were removed. |
| Repository validation | disposable forest1 PostGIS / DB30A image | Ran | Ruff passed for server and executor; all 212 Django tests passed with one expected skip; two independent clean builds matched at SHA-256 `8ceb8e94b1ec494c69ba32ef99596bc6ec5ebd6b884b47a7580d36b5b28f2476`; shell syntax, JSON parsing, secret scan, and `git diff --check` passed. |

### Findings and deviations

- The captured legacy Gate Creek polygon does not contain 221 existing
  subcatchments and one existing channel; no invalid child geometry was found
  and DB30A preserved the exact source geometry rather than rewriting history.
- The private content-addressed baseline is complete and exact, but the
  already-declared public `/artifacts` URI currently routes to the 699-byte
  frontend document instead of the requested manifest/object.
- Production adoption itself passed. The required real materialized query
  exposed the serving gap, so the exact rehearsed rollback ran and left the
  service on its verified `EMPTY` legacy fallback.

### Terminal disposition

- Final status: `EXECUTED-HOLD-PUBLIC-ARTIFACT-SERVING`
- Exit criteria disposition: all capture, backup, restore, export, rebuild,
  adoption, rollback, fallback, integrity, and cleanup gates passed; active
  durable capability serving did not.
- Blocker, if held: the declared public artifact namespace does not serve the
  operator-owned checksum-addressed bytes retained under `forest1:/wc1`.
- First follow-on action, if held: DB30B should expose that existing namespace
  read-only, prove exact representative manifest/TIFF/Parquet reads, and then
  re-adopt the retained reviewed baseline by its exact manifest hash.
- Successor package: DB30B; DB31 remains blocked until DB30B closes DB30A.

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
