# Database Deployment Architecture Review Disposition

Review date: 2026-07-16

Reviewed document:
[Database Deployment Architecture and Tooling Specification](database-deployment-architecture.md)

An independent review cross-checked the proposed architecture against the
current Compose configuration, GitHub deployment workflow, production
entrypoint, watershed loader, download cache, writers, inventory, API identity
behavior, and deployment documentation.

The initial review produced 18 findings. A closure pass found four incomplete
dispositions and one new contradiction. All initial and closure findings were
accepted and incorporated into the specification or related safety
documentation. No finding was rejected or dismissed as prose-only. “Accepted”
here means the requirement is now part of the design; it does not mean the
corresponding production implementation has already occurred.

## High-severity findings

| ID | Finding | Disposition |
| --- | --- | --- |
| H1 | `dataset_key` ambiguously represented both a collection and an individual watershed. | Accepted. The spec now requires distinct immutable `collection_key` and `watershed_key` values, replaceable run IDs, and explicit split/merge/replacement lineage. Manifest schema work is blocked until this distinction is implemented. |
| H2 | A single tracked plan could not represent production upgrade, rollback, staging, and empty-build bases. | Accepted. Target manifests no longer contain an intrinsic plan. Forward, exact inverse, and empty-build plans are separately keyed by base, target, contract, materializer, and fingerprint versions. |
| H3 | A PostgreSQL session advisory lock could not span the proposed separate command processes. | Accepted. The host orchestrator owns a durable attempt lease; activation locks the singleton active-release row, reasserts the base, recomputes the plan, and takes a transaction advisory lock. The legacy loader must be production-gated. |
| H4 | Code/schema deployment could race data deployment. | Accepted. Both workflows must share one GitHub concurrency group, canonical host lock, Compose project, and compatibility checks. Migrations become an explicit one-shot deployment step. |
| H5 | Adding a named PostgreSQL volume without migrating the anonymous volume would start an empty database. | Accepted. Phase 0 now requires a pinned-version, off-host-backed-up, quiesced restore/cutover runbook that retains the old volume through acceptance. |
| H6 | The staging representation was unspecified. | Accepted. Version 1 uses fixed, logged, migration-created, attempt-scoped staging tables with bounded-memory loading, constraints, space preflight, leases, and recovery cleanup. |
| H7 | Root-level release files are unavailable in the current server image. | Accepted. Production tooling runs from a one-off code/toolchain-only release-tool image built from the repository root and pinned by digest. Manifests and plans are excluded from the image and mounted read-only or fetched by verified hash. |
| H8 | Wildcard deletion authorization contradicted exact desired state. | Accepted. Globs are prohibited. Every removal is an exact reviewed run ID or a hashed exact set derived from an identified base collection. |
| H9 | RHESSys declarations had no atomically activated runtime representation. | Accepted. The spec now requires serving capability rows containing mode, durable base URI, immutable index, and runtime configuration, activated with watershed rows. The inventory also marks current WEPPcloud locations as observed state pending durable copying. |

## Medium-severity findings

| ID | Finding | Disposition |
| --- | --- | --- |
| M1 | Attempts abandoned outside `applying` had no recovery semantics. | Accepted. Attempts have owner, heartbeat, and expiry fields; `data_release recover` terminalizes expired attempts and cleans staging. A singleton `ActiveDataRelease` provides one lockable state row, initially `EMPTY` and later `ACTIVE`. |
| M2 | Replacing child rows would change public GeoJSON feature IDs. | Accepted. Reconciliation must upsert retained business identities in place and preserve primary keys, or a compatible stable-feature-ID API migration must occur first. |
| M3 | Child identity and Parquet join semantics disagreed. | Accepted. Data-contract version 1 defines subcatchment identity and Parquet cardinality on `(watershed, topazid)`. A production audit found no duplicate `topazid` within a watershed. Other keys require a new contract. |
| M4 | Idempotency included unavoidable audit writes and was required before reconciliation existed. | Accepted. Idempotency is now defined over domain, capability, active-pointer, and artifact state; audit attempts may append. Repeat-apply proof moved to the reconciliation phase. |
| M5 | Compatibility specified only a minimum migration. | Accepted. Releases now lock schema signature or bounded migrations, data-contract range, code/toolchain-only materializer image digest and Git revision, fingerprint algorithm, and output-affecting toolchain versions. The image digest is resolved before manifests and plans are generated. |
| M6 | Rollback was not a preapproved executable workflow. | Accepted. CI generates an exact inverse plan, artifacts are retained, and a dedicated rollback command asserts the currently active failed target. |
| M7 | Backup durability, RPO, and retention were left as optional decisions. | Accepted. Destructive operations require verified encrypted off-host backups. Scheduled off-host backup with a 24-hour default RPO is a Phase 0 requirement now, and retention covers the active plus two rollback releases. |
| M8 | Related documentation still recommended unsafe reset behavior and overstated current loader coverage. | Accepted. `DEPLOYMENT.md` no longer recommends `down` plus forced reload or the broken NASA filtered-download path, and the inventory distinguishes observed loader configuration from approved target state and rejects current `--dry-run` as validation. |
| M9 | Production database exposure and temporary secret-file handling were omitted. | Accepted. Phase 0 now requires removing or loopback-binding the database host port and using mode-`0600`, minimized, reliably cleaned environment files. |

## Closure-pass findings

| ID | Finding | Disposition |
| --- | --- | --- |
| C1 | Embedding digest-bearing manifests and plans in the materializer image made its digest self-referential. | Accepted. The image contains code and toolchain only. Its digest is resolved first; manifests and plans reference it and are supplied separately by verified hash. |
| C2 | An empty build had no active-release row to lock. | Accepted. The ledger migration creates one lockable singleton in explicit `EMPTY` state with a nullable release pointer; first activation transitions it to `ACTIVE`. |
| C3 | The inventory still treated TTL-managed WEPPcloud RHESSys paths as accepted target hosting. | Accepted. Those paths are now labeled observed current state, and all accepted capabilities require verified durable project copies and immutable indexes before activation. |
| C4 | Production documentation still advertised `download_data --runids`, which silently skips NASA because of its custom master filename. | Accepted. The production command was removed and the limitation is documented until code and regression tests fix it. |
| C5 | Scheduled backups remained conditional even though non-watershed tables are already persistent by design. | Accepted. Scheduled encrypted off-host backup with a 24-hour default RPO is required in Phase 0 now. |

## Defaults adopted from review

- Operator-owned artifact backups on `forest1:/wc1` with private modes,
  content-addressed verified copies, and no TTL for retained releases.
- All non-watershed Django tables are persistent by default.
- Mandatory stable watershed keys are introduced before release schema
  implementation.
- Reviewed hashed batch-member indexes are authoritative.
- Metadata authority is defined field by field and unresolved conflicts fail.
- Accepted RHESSys assets move out of TTL-managed storage.
- Production release deployment remains manual and independently approved.
- The active release plus two rollback releases and their supporting artifacts,
  plans, reports, and backups are retained.
- The pinned release-tool image digest is the reproducibility boundary.

## Verification performed during disposition

A read-only query of production on 2026-07-16 confirmed:

- zero duplicated `(watershed_id, topazid)` subcatchment identities; and
- zero duplicated `(watershed_id, topazid, weppid)` subcatchment identities.

This supports the proposed version-1 Parquet join contract but does not replace
validation of every future release artifact.

## Remaining implementation status

The architecture and documentation findings are dispositioned. DB25 implements
the repository workflow/host serialization, explicit migration, compatibility,
and database-role contract. Production role/credential installation and schema
rollout remain DB27A work, while the database deploy tool and protected release
workflow remain DB26/DB27 work and must follow the phased plan in the
specification.
