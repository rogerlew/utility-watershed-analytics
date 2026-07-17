# Database Deployment Roadmap Dual-Review Disposition

Review date: 2026-07-16

Reviewed document: [Utility Watershed Analytics Roadmap](ROADMAP.md)

Reviewed pre-disposition SHA-256:
`bc8d8cc16e0e5ffeb0ec9b8496ec7e8a2b7547ad39d16fc35c35ac215d9a0e2b`

Starting repository commit:
`47fced02b28420edfc1bce35ef7ba8ed177ca02d`

Two independent read-only agents reviewed the proposed package campaign. One
focused on data/system architecture and code-path compatibility; the other
focused on operations, security, backup, recovery, and production sequencing.
Neither agent edited the working tree. The author then performed a closure pass
against both reviews and the architecture acceptance criteria.

“Accepted” means the roadmap now assigns the requirement to a package with an
explicit proof boundary. It does not mean the implementation or production
operation has occurred.

## Data and system architecture findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| D1 | High | A populated legacy production database had no valid release-ledger bootstrap, base manifest, or source-independent exact inverse. | Accepted. DB21A implements canonical legacy export, rebuild, fingerprint, and guarded adoption tooling without changing existing watershed/child/non-watershed rows; it permits only an exact reviewed capability-bootstrap set in the atomic adoption transaction. DB30A captures and adopts the actual production base after compatible schema/code rollout, retaining old NASA and former Mill state as immutable rebuild artifacts. DB22 requires the mechanism; DB31 binds its plans to the adopted base. |
| D2 | High | No package migrated server/client capability reads from hard-coded run IDs and live WEPPcloud discovery to `RunCapability`. | Accepted. DB19A owns server and client integration, durable indexed reads, removal of hard-coded eligibility and derived URLs, and a state-specific transition: an exact observable fallback may probe only while the ledger is `EMPTY`; after DB30A atomically makes it `ACTIVE`, absent capability rows fail closed without probing. DB21 exercises both sides. |
| D3 | Medium | The first release candidate promised forward/inverse/empty plans without depending on the implemented planner. | Accepted. DB31 now depends directly on DB22 and DB30A and must name the adopted baseline manifest and fingerprint used by forward and inverse plans. |
| D4 | Medium | The stable-identity migration could have been satisfied by merely adding `watershed_key` while retaining mutable `runid` as relational identity. | Accepted. DB13 now requires separation of immutable logical identity from current source revision, alias/redirect behavior, child-FK expand/backfill/compatibility sequencing, and a replacement proof that preserves relational and feature identity. |
| D5 | Medium | Empty build and reconciliation could have developed separate writer semantics. | Accepted. DB20 owns canonical attempt-scoped staged rows and `EMPTY`-base mutation primitives; DB23 must reuse them for non-empty bases; DB24 compares clean-build and reconciliation fingerprints for the same target. |
| D6 | Medium | Idempotency evidence omitted the active pointer, activation timestamp, immutable artifacts, and no-backup no-op behavior. | Accepted. DB24 now covers the complete state boundary and allowed audit-only append behavior. DB26 proves an already-active deployment takes no backup and performs no serving rewrite. |

The data review found no additional issue with exact membership/removal
authorization, metadata and geometry precedence, NASA enrichment,
fingerprinting contracts, child business keys, failure atomicity, deployment
serialization, or coverage of the named first-release datasets.

## Operations, security, and recovery findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| O1 | High | The unmanaged populated base made the first forward/inverse deployment operationally impossible. | Accepted with D1 through DB21A and DB30A. Backup-only rollback cannot be substituted silently; failure to create source-independent inverse artifacts is a terminal hold. |
| O2 | High | Migration packages existed, but no package deployed their prerequisite schema and dual-compatible code to production before base adoption. | Accepted. DB27A owns the separately authorized, locked, backed-up production compatibility rollout and proves current rows/APIs remain compatible before adoption. |
| O3 | High | Early Compose/systemd convergence could detach the anonymous database volume by invoking the legacy `down` behavior or changing project identity. | Accepted. DB02 defines a no-`down`, no-database-recreate interim/final contract. DB03 neutralizes unsafe stop behavior and restarts only app services while preserving exact database identities. DB05 combines final convergence with the explicit named-volume target. |
| O4 | High | Backup, deployment, restore, volume, and systemd principals did not share one composable host-lock protocol; nested backup could deadlock. | Accepted. DB02 now owns one absolute cross-principal lock contract, participating operations, permissions, shared/exclusive or inherited-token behavior, cancellation, reboot, and nested invocation tests. DB03, DB05, DB25, and DB26 consume it. |
| O5 | High | Gate Creek and Victoria target packages covered RHESSys but not all ordinary immutable watershed build inputs. | Accepted. DB28 now freezes Victoria membership and publishes every required ordinary Gate/Victoria input as well as accepted RHESSys assets; DB31 clean-builds without upstream access. |
| O6 | Medium | Backup policy conflated rolling persistent-state backups with release retention and omitted an accepted RTO, key recovery, pruning, alert-failure, reboot, and post-runtime-change requalification. | Accepted. DB01 separates time-based and release-point retention, must approve both RPO and maximum RTO, provisions capacity accordingly, and terminates on hold when the restore drill misses the objective. DB03 and DB05 require successful scheduled cycles after their changes; DB05 also requires a post-cutover restore test. |
| O7 | Medium | Volume-cutover proof omitted explicit quiescence, roles/extensions/sequences, source preservation against prune, and an exercised rollback. | Accepted. DB05 now names those controls, fresh backup timing, stable source reference, and post-cutover backup/restore. DB05A is the separately authorized exact-ID deletion package after the rollback window. |
| O8 | Medium | “Production-shaped staging” lacked fidelity, masking, access, drift, and destruction requirements. | Accepted. DB32 defines base age/fingerprint, versions, scale, geometry, disk/WAL, concurrency/network shape, deviations, sensitive-data masking, isolated credentials, retention/destruction, and approval invalidation on base drift. |
| O9 | Medium | An artifact-store contract did not provision or accept real bucket/IAM/KMS/versioning/lock infrastructure. | Accepted. DB10A is an explicit infrastructure acceptance package with separate roles, immutable-read and deletion-recovery tests, rotation, monitoring, and break-glass recovery. DB12 depends on it. |
| O10 | Medium | Least-privilege database roles had no owner. | Accepted. DB25 owns planner, staging, activation, runtime, backup, migration, and restore/break-glass roles plus negative permission and rotation tests. DB27A verifies them in production. |
| O11 | Medium | Network hardening named PostgreSQL but not the directly published application port. | Accepted. DB02 now inventories every listening socket, restricts internal published ports, tests reachability from Compose, localhost, Tailscale, and public interfaces, and records firewall assumptions. |
| O12 | Medium | Durable deployment execution lacked reboot/no-blind-restart behavior and secure off-host audit spool requirements. | Accepted. DB26 defines the execution principal, oneshot behavior, signals/timeouts, reboot injection, recover-before-resume, protected secret-scanned logs/reports, off-host copy, retention, cache invalidation, and stale-attempt alerts. |
| O13 | Medium | The release candidate lacked a direct planner/base dependency. | Accepted with D3 in DB31. |
| O14 | Low | The global gates did not distinguish read-only, runtime, schema, activation, restore, and emergency-loader authority. | Accepted. An operation-to-gate matrix now follows the campaign gates. |
| O15 | Low | Final activation could have reused an ordinary scheduled backup instead of creating a fresh pre-activation off-host backup. | Accepted. DB33 requires a fresh backup after final preflight/staging, verified off-host copy, age and hash recording, and explicitly rejects the ordinary scheduled backup as sufficient. |

The operations review found no additional issue with exact-base/hash binding,
wildcard prohibition, removal thresholds, empty-upstream failure, transaction
and active-row locking, logged staging, failure-state separation, protected
manual activation, RHESSys durability policy, or the distinction between
inverse reconciliation and full backup restore.

## Closure-pass additions

The disposition pass also made requirements that were present in the
architecture but easy to lose at package boundaries explicit:

- DB05 owns maintenance mode, write quiescence, and full role/extension/
  sequence verification.
- DB08 prohibits credentials and credential-bearing URLs in release files.
- DB10 records artifact licensing, sensitivity, residency, and retention.
- DB16 includes WAL and backup space in preflight margins.
- DB21 rejects HTML error bodies saved as artifacts and validates area deltas
  and removed-run behavior.
- DB23 regenerates simplified geometry when source geometry changes.
- DB26 owns worker cache invalidation or restart after activation.
- DB01 documents protected operational-account recreation for disaster rebuild.

The two reviewers then performed a read-only closure pass. Three residual
contradictions were accepted and corrected:

- DB21A now explicitly permits only the reviewed capability-bootstrap insert
  during adoption and rolls ledger and capability changes back together.
- DB19A's compatibility behavior is state-specific: the exact legacy fallback
  may probe only in `EMPTY`; `ACTIVE` with no capability fails closed.
- Legacy adoption has its own operation-gate row and DB30A must rehearse and
  exercise rollback to `EMPTY` plus fallback. DB01 must approve and meet an RTO,
  not merely measure one.

Both reviewers rechecked those corrections and returned explicit closure with
no remaining contradiction in their review scopes.

## Final review status

All actionable findings are accepted and dispositioned in the roadmap. No
finding was dismissed as documentation-only, and no production execution has
been authorized by this review. The package sequence must still be reconciled
as packages complete or terminate on hold.
