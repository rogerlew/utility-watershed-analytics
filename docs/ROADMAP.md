# Utility Watershed Analytics Roadmap

Status: Living — forward-only queue

Last reconciled: 2026-07-16

This document orders unfinished work. It is not a history and it does not, by
itself, authorize execution or production mutation. Completed work moves to
the [work-package catalog](work-packages/README.md); durable design decisions
and operational facts remain in their authoritative specifications and
inventories.

The roadmap and work-package workflow are adapted from the governance in
`cligen-rs` at commit `7adce50`, with that project's scientific milestones and
Rust-specific gates replaced by this repository's requirements.

The initial queue covers the database release and production-safety work that
is already specified. It does not imply that the application has no other
product work; add independently ordered tracks as those outcomes are defined.

## How to use this roadmap

1. Select the next unblocked roadmap item.
2. Scaffold one bounded work package under `docs/work-packages/` and link the
   roadmap item from it.
3. Review scope, authority, dependencies, gates, dispatch coordinates, and
   production permissions before authorizing execution.
4. Execute the package and record evidence honestly as Ran, Static, or Mixed.
5. Close the package as complete or on an explicit hold, update the catalog,
   and reconcile this queue. Never silently abandon or reuse an identifier.

One package may cover more than one roadmap item only when their acceptance
criteria cannot be tested independently. One roadmap item may require multiple
successor packages, but each successor receives a new package identifier.

## Ordering principles

- Protect and recover production before introducing destructive data changes.
- Define stable identity and data contracts before release schemas and tools.
- Resolve, enrich, fingerprint, and validate inputs before database mutation.
- Prove clean builds before relying on reconciliation.
- Implement exact plans, rollback, locking, and recovery before automation.
- Copy RHESSys assets to durable project storage before advertising capability.
- Treat code, Django schema, data-contract, materializer, artifact, and runtime
  compatibility as independent checks.
- Preserve user and application state while rebuilding derived watershed data.

## Active execution package

None. The next recommended package is **P0A — Backup and restore baseline**.
Creating a package does not authorize access to production; its authority must
state explicitly which read-only and mutating operations are allowed.

## Forward queue

### P0 — Production safeguards

| ID | Outcome | Dependencies | Exit signal |
| --- | --- | --- | --- |
| P0A | Backup and restore baseline | None | Scheduled encrypted off-host backups meet the accepted RPO and retention policy, and a documented restore drill verifies a usable backup. |
| P0B | Canonical and serialized deployment surface | P0A for production changes | The PostGIS image is pinned without an incidental upgrade; one checkout, Compose project, and production Compose file are canonical; code and data operations share a host lock; database exposure and temporary secrets are hardened. |
| P0C | Named PostgreSQL volume cutover | P0A, P0B | A quiesced, backed-up, reversible runbook moves production from the anonymous volume to the named volume and retains the source volume through acceptance. |

### R1 — Release representation

| ID | Outcome | Dependencies | Exit signal |
| --- | --- | --- | --- |
| R1A | Stable identity and manifest contracts | P0 safeguards may proceed in parallel | Versioned schemas define collection keys, watershed keys, replaceable run IDs, exact batch membership, field-level metadata authority, lineage, and compatibility signatures. |
| R1B | Immutable artifact store and local content cache | Artifact-provider decision, R1A identity | Content-addressed artifacts, checksums, retention, encryption, access roles, and cache verification are implemented without TTL for retained releases. |
| R1C | Base-specific plan representation | R1A | Forward, exact inverse, and empty-build plans are keyed to explicit base state, target release, schema/data contracts, materializer digest, and fingerprint versions; removals are exact rather than wildcarded. |

### B1 — Strict preparation and clean build

| ID | Outcome | Dependencies | Exit signal |
| --- | --- | --- | --- |
| B1A | Reproducible release-tool image | R1A | A code-and-toolchain-only image is built from the repository root, pinned by digest, and consumes manifests and plans separately by verified hash. |
| B1B | Deterministic preparation and enrichment | R1A, R1B, B1A | Required source failures are fatal; the NASA 202606 resources enrichment contract is automated; exact batch and RHESSys indexes and validation reports are produced. |
| B1C | Clean-build proof | B1B | An empty database build satisfies integrity and application checks, and two independent builds produce identical watershed-domain fingerprints. |

### C1 — Transactional reconciliation

| ID | Outcome | Dependencies | Exit signal |
| --- | --- | --- | --- |
| C1A | Release ledger and recoverable staging | R1C, B1C | Active-release, attempt-lease, per-run state, capability, and migration-created staging models support bounded loading, expiry, cleanup, and recovery. |
| C1B | Atomic desired-state reconciler | C1A | Upserts preserve retained public identities; deletions match the exact approved plan; unexpected bases or removal thresholds fail; non-watershed state is preserved. |
| C1C | Idempotency, rollback, and failure proof | C1B | Repeat apply produces no domain changes, missing inputs leave active state unchanged, and the exact inverse rollback restores the prior compatible release. |

### D1 — Deployment integration

| ID | Outcome | Dependencies | Exit signal |
| --- | --- | --- | --- |
| D1A | Shared code/data deployment controls | P0B, C1C | Code migrations and data activation use one production concurrency group and host lock, explicit compatibility checks, and explicit one-shot migrations. |
| D1B | Production data-deploy command | P0A, D1A | `scripts/deploy_database.sh` performs preflight, verified backup, reviewed base-specific planning, activation, smoke tests, reporting, and exact rollback without interactive-session dependence. |
| D1C | Protected release workflow | D1B | CI prepares and validates releases; a protected manual action with independent approval deploys an immutable reviewed release; merge alone cannot mutate production. |

### E1 — First authoritative data release

| ID | Outcome | Dependencies | Exit signal |
| --- | --- | --- | --- |
| E1A | Durable RHESSys assets and indexes | R1B, B1B | Accepted Gate Creek, Victoria members, and successor Mill Creek assets are copied, indexed, checksum-verified, and sample-read from project-controlled durable storage. |
| E1B | Exact target release prepared | B1C, E1A | The release retains Gate Creek and Victoria; replaces former Mill Creek with `some-oligopoly`; replaces `nasa-roses-2026-sbs` with enriched `nasa-roses-202606-psbs`; adds `bremerton-2026-psbs`; and encodes every approved membership or metadata change exactly. |
| E1C | Staging validation and production rollout | D1C, E1B | Staging passes the full release contract and application smoke tests; backup and rollback are verified; production activates the release; the inventory snapshot and release report are reconciled. |

The authoritative target membership and acceptance details for E1 remain in
the [database inventory](database-inventory.md). The implementation and safety
contract remains in the
[database deployment architecture](database-deployment-architecture.md).

## Independent compatibility axes

A package must identify every axis it changes and test the corresponding
boundary. A release is not compatible merely because Django migrations pass.

| Axis | Examples of locked or checked state |
| --- | --- |
| Application code | Git revision, API expectations, public identity behavior |
| Django schema | Migration set or schema signature and integrity constraints |
| Data contract | Manifest, batch-index, child identity, and fingerprint versions |
| Materializer | Release-tool image digest and output-affecting tool versions |
| Artifacts | Content hashes, transformation lineage, and exact membership indexes |
| Capabilities | RHESSys mode, durable base URI, immutable index, and runtime configuration |
| Active base | Current release identity and domain fingerprint used to generate a plan |

## Open decisions

These decisions can be investigated in bounded packages. Production activation
must not assume an unresolved answer.

1. Select the S3-compatible provider, bucket ownership, encryption keys, and
   access roles for durable artifacts and backups.
2. Define watershed-key names for existing members and the future public-route
   migration and redirect policy.
3. Complete the field-level metadata precedence matrix for every collection.
4. Define the activation lock-time and API-latency budget that would trigger a
   blue-green design.
5. Decide whether persistent application state needs an RPO shorter than the
   current 24-hour default.
6. Assign prepare, approve, deploy, and rollback roles and separation rules.

## Deferred work

- Blue-green database or versioned-schema activation, until measured staging
  and activation time justifies it.
- Automatic production data deployment on merge.
- Public-route migration from run ID to watershed key; creating the key is not
  deferred.
- New persistent product features or saved user analyses unrelated to the data
  release system.
- Unrelated application enhancements discovered while executing a package.

## Reconciliation rules

- A package closed `EXECUTED-COMPLETE` removes its delivered item from this
  forward queue; its evidence remains in the catalog.
- A package closed `EXECUTED-HOLD-<REASON>` records the blocker and first
  follow-on action. Any successor gets a new package ID, and this roadmap is
  updated to show the actual remaining outcome.
- A scope change is written into the package before execution continues.
- New facts update the authoritative inventory or specification, not only a
  package artifact.
- Roadmap IDs and package directory names are never reassigned to different
  work.
