# Utility Watershed Analytics Roadmap

Status: Living — forward-only queue

Last reconciled: 2026-07-18

This document orders unfinished work. It is not a history and it does not, by
itself, authorize execution or production mutation. Completed work moves to
the [work-package catalog](work-packages/README.md); durable design decisions
and operational facts remain in their authoritative specifications and
inventories.

The roadmap and work-package workflow are adapted from the governance in
`cligen-rs` at commit `7adce50`, with that project's scientific milestones and
Rust-specific gates replaced by this repository's requirements.

The implementation campaign received independent data/system and
operations/security reviews. All actionable findings are dispositioned in the
[dual-review record](database-deployment-roadmap-review.md).

The initial queue covers the database release and production-safety work that
is already specified. It does not imply that the application has no other
product work; add independently ordered tracks as those outcomes are defined.

## How to use this roadmap

1. Select the next unblocked package candidate.
2. Scaffold it under `docs/work-packages/YYYYMMDD-<package-slug>/` and preserve
   its roadmap ID in `package.md`.
3. Review scope, authority, dependencies, gates, dispatch coordinates, and
   production permissions before authorizing execution.
4. Execute the package and record evidence honestly as Ran, Static, or Mixed.
5. Close the package as complete or on an explicit hold, update the catalog,
   and reconcile this queue. Never silently abandon or reuse an identifier.

The entries below are package candidates, not pre-authorized work and not empty
package directories waiting to be filled. Scaffold a directory only when the
package is ready for scope and authorization review. If execution exposes
successor work, give it a new roadmap and package identifier rather than
expanding the active package indefinitely.

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

No production mutation package is currently active. Wave 0 production-safety
packages DB01 through DB05 are complete:

- [DB01](work-packages/20260716-db01-backup-restore-baseline/package.md) is
  `EXECUTED-COMPLETE` after permanent restricted transport, production
  scheduling, encrypted backup, success/failure/freshness, journal alerting,
  exact isolated restore, application smoke, a 376-second RTO, and post-reboot
  timer/snapshot persistence passed.
- [DB02](work-packages/20260716-db02-production-runtime-bundle/package.md) is
  `EXECUTED-COMPLETE` after the fail-closed target runtime, isolated gates,
  exact production identity freeze, current reachability matrix, and DB03
  adoption boundary passed without production mutation.
- [DB03](work-packages/20260716-db03-production-runtime-convergence/package.md)
  completed host convergence; its historical publication hold is resolved by
  DB03A.
- [DB03A](work-packages/20260717-db03a-production-runner-ownership-closure/package.md)
  is `EXECUTED-COMPLETE`: fork `main`, protected secret delivery, verified
  runner installation, online/idle state, old-runner disablement, unchanged
  production, and temporary-privilege removal passed without job dispatch.
- [DB04](work-packages/20260716-db04-legacy-loader-guardrails/package.md) is
  `EXECUTED-COMPLETE`: destructive legacy loader selections reject before any
  database query, production Silk is disabled, and all isolated repository and
  production-image gates passed without production access.
- [DB05](work-packages/20260716-db05-named-postgres-volume-cutover/package.md)
  is `EXECUTED-COMPLETE`. Its exact-image production anonymous-to-named
  cutover, actual rollback/reapply, restart/recreation, reboot, fork checkout,
  encrypted pre/post backups, exact fingerprints, and isolated post-backup
  restore all passed. Fork `main` and the canonical production checkout were
  cleanly fast-forwarded through the reviewed DB05 history; runtime identity
  and public health remained exact without a service restart.
- [DB06](work-packages/20260716-db06-domain-identity-audit/package.md) is
  `EXECUTED-COMPLETE`: repository mapping and tests passed, and the separately
  authorized aggregate-only production audit found 126 watersheds, 195,457
  subcatchments, and 86,895 channels with zero duplicate groups or child
  orphans and no production mutation.
- [DB07](work-packages/20260717-db07-identity-metadata-contract/package.md) is
  `EXECUTED-COMPLETE`: stable collection/watershed keys, source aliases, child
  identities, split/merge/removal lineage, route compatibility, and the
  field-level authority matrix are frozen. Nine accepted and three rejected
  fixtures plus seven validator/model-coverage tests passed.
- [DB08](work-packages/20260717-db08-release-index-schemas/package.md) is
  `EXECUTED-COMPLETE`: seven version-1 release/index schemas, seven positive
  fixtures, nine negative cases, bounded semantic validation, and the reusable
  data-contract CI gate passed without production access.
- [DB09](work-packages/20260717-db09-fingerprint-plan-contract/package.md) is
  `EXECUTED-COMPLETE`: five versioned semantic fingerprint subjects, golden and
  mutation proof, and strict forward, exact-inverse, and empty-build plan
  contracts passed with exact wrong-base replay rejection.
- [DB10](work-packages/20260717-db10-artifact-store-contract/package.md) is
  `EXECUTED-COMPLETE`: the original provider choice was superseded by the
  operator's authoritative `forest1:/wc1` decision; private filesystem storage,
  content hashes, active-plus-two retention, six artifact classes, and seven
  failure cases are frozen and CI-validated.
- [DB10A](work-packages/20260717-db10a-artifact-store-infrastructure/package.md)
  is `EXECUTED-COMPLETE`: the real forest1 artifact backup tree was provisioned
  with private test/production namespaces; three test releases, negative
  integrity cases, idempotent rerun, and an exact clean restore passed.
- [DB11](work-packages/20260717-db11-release-tool-foundation/package.md) is
  `EXECUTED-COMPLETE`: all eight command names, stable JSON events and exit
  codes, verified read-only input, explicit unavailable-command failures, and a
  non-root code-only image passed unit, double-build, content-audit, and
  digest-pinned runtime proof.
- [DB12](work-packages/20260717-db12-artifact-client-cache/package.md) is
  `EXECUTED-COMPLETE`: streaming immutable publication/fetch, checksum and cache
  verification/recovery, concurrent fetch, typed failures, private paths,
  namespace isolation, and bounded retained/leased cache cleanup passed unit,
  real-forest1 temporary acceptance, and reproducible image proof.
- [DB13](work-packages/20260717-db13-watershed-identity-migration/package.md) is
  `EXECUTED-COMPLETE`: additive internal identities, reviewed stable keys,
  permanent run aliases, dual child links, stable-key routes, validation, old
  model compatibility, canonical browser redirects, replacement preservation,
  and bounded rollback passed server/client and production-shaped isolated
  PostGIS proof.
- [DB14](work-packages/20260717-db14-domain-integrity-constraints/package.md) is
  `EXECUTED-COMPLETE`: compatibility and partial logical child keys, stable-key
  and status checks, fail-closed Topaz joins, exact three-table rebuild
  ownership, negative fixtures, and production-shaped migration/rollback and
  lock measurement passed in isolated PostGIS.
- [DB15](work-packages/20260717-db15-release-ledger-capabilities/package.md) is
  `EXECUTED-COMPLETE`: immutable version-1 release coordinates, one bootstrapped
  `EMPTY` singleton, attributable attempts and one bounded lease, per-run and
  artifact history, sanitized failures, and atomic active-only RHESSys
  capability visibility passed isolated lifecycle and scale migration proof.
- [DB16](work-packages/20260717-db16-staging-recovery-schema/package.md) is
  `EXECUTED-COMPLETE`: five fixed logged attempt-scoped tables, exact six-part
  capacity preflight, bounded chunk loading and heartbeat, crash residue,
  planning/staging/applying expiry, diagnostic retention, cleanup failure/retry,
  and active-serving preservation passed isolated integration and scale proof.
- [DB17](work-packages/20260717-db17-source-resolution-indexes/package.md) is
  `EXECUTED-COMPLETE`: strict standalone and batch preparation, exact reviewed
  membership, required-source and format failures, immutable local publication,
  DB08 index generation, and credential-free receipt replay passed unit,
  schema, real-forest1 temporary acceptance, and reproducible image proof.
- [DB18](work-packages/20260717-db18-nasa-202606-enrichment/package.md) is
  `EXECUTED-COMPLETE`: the fixed checksum-pinned `WWS_Code` transform preserves
  target membership, order, run IDs, geometry, and other fields; exact approved
  values, conflicts, unmatched counts, DB08 provenance, and immutable replay
  passed synthetic unit, schema, forest1, and reproducible image proof.
- [DB19](work-packages/20260718-db19-rhessys-artifact-tooling/package.md) is
  `EXECUTED-COMPLETE`: closed dynamic/precomputed descriptors, exact scenario
  coverage, Parquet footer schemas, GeoTIFF metadata/sample reads, geometry
  compatibility, immutable local publication, removal difference, and replay
  passed synthetic unit, schema, forest1, and reproducible image proof.
- [DB19A](work-packages/20260718-db19a-capability-runtime-integration/package.md)
  is `EXECUTED-COMPLETE`: one state-first resolver now owns RHESSys and SBS
  eligibility; exact observable `EMPTY` fallback switches off atomically in
  `ACTIVE`; declared durable catalog, tile, geometry, query, and download paths
  and API-driven client controls passed synthetic server/client proof.
- [DB20](work-packages/20260718-db20-strict-empty-builder/package.md) is
  `EXECUTED-COMPLETE`: checksum-locked ordinary artifacts now produce canonical
  bounded attempt staging and one atomic EMPTY-base watershed, child, and
  capability build. Multi-run mixed-source, deterministic replay, bad required
  input, and late rollback proof passed disposable PostGIS without production
  access.
- [DB21](work-packages/20260718-db21-clean-build-reproducibility/package.md) is
  `EXECUTED-COMPLETE`: fatal artifact, staging, database, application, and
  report validation now wraps the DB20 clean build. Two independent disposable
  builds produced byte-identical bounded domain/capability fingerprints, while
  unsafe artifacts and invalid geometry failed before acceptance.
- [DB21A](work-packages/20260718-db21a-legacy-base-tooling/package.md) is
  `EXECUTED-COMPLETE`: reviewed stable identities, DB20-compatible
  content-addressed legacy export, source-independent exact rebuild, and
  transactional adoption/rollback preserve every pre-existing domain row while
  changing only ledger, pointer, attempt, and reviewed bootstrap capability
  state.

The reviewed DB02/DB03 changes and DB03A safe workflow are published to the
fork's `main`. The fork-owned `wepp3` runner is online and idle; the old
upstream-owned local runner remains disabled. No DB03A workflow was dispatched.
The safe unit is enabled, server port 8000 is closed, the
canonical lock and protected runtime are installed, application rollback and
safe unit behavior passed, and canonical locked snapshot `4361efe3...` is
verified. Production uses the DB05 named database volume while the exact
anonymous source remains held and prune-prohibited. Temporary sudo was removed.
DB04 is repository-complete but not deployed to production. The S1 contract
freeze, DB10A local infrastructure acceptance, DB11–DB12 release-tool and
artifact-client foundations, DB13 stable identity expansion, and DB14 domain
integrity, DB15 release-ledger foundations, DB16 staging/recovery, DB17 strict
source preparation, DB18 NASA enrichment, DB19 RHESSys artifact tooling, and
DB19A materialized capability runtime integration, DB20 strict empty-build
materialization, DB21 clean-build validation/reproducibility, and DB21A
legacy-base export/adoption tooling are complete. DB22 base-aware planning and
exact inverse generation is the next recommended package.

## Execution environments and Wave 0 readiness

- `forest1` is the shared development server for repository authoring, tests,
  and isolated non-production rehearsals.
- `wepp3` is the production server. Repository work on `forest1` does not
  authorize inspection or mutation of `wepp3`.

The 2026-07-16 [Wave 0 environment readiness record](wave-0-readiness.md)
concludes that `forest1` is ready to start repository-only DB01 and DB02 work.
The local database/API subset also starts cleanly after the operator released
ports 8000 and 5432, and DB01 passed its encrypted empty-development rehearsal.
On 2026-07-16, a separately authorized bounded drill backed up the
non-empty `wepp3` database, published an encrypted snapshot on `forest1`, and
passed exact isolated restore plus representative application smoke in 387
seconds without changing the serving stack. A later no-reboot task installed
the permanent restricted `wepp3` transport and backup/freshness user timers,
published scheduled snapshot
`1db1e3a475748e86692a26f5da0127e23399a2a2833a715bd68fd11133592359`,
proved normal and stale freshness paths plus journal notification, and passed
the installed exact restore and non-empty smoke in 376 seconds. The operator's
2026-07-17 reboot then proved both backup timers, freshness, and encrypted
snapshot access persist. The accompanying apt/Compose upgrade exposed a
separate unsafe legacy serving unit; the exact existing containers were
recovered without recreate. DB02 then froze the production identities and
current reachability, confirmed the registration remains `not-found`, and
completed the repository-owned fail-closed contract without changing
production. Port 5173 remains assigned to an unrelated development service,
the ignored pgAdmin definition is absent, and the copied WEPPcloud tokens are
expired.

## Database deployment implementation campaign

This is the topological execution order for implementing the
[database deployment architecture](database-deployment-architecture.md). IDs
are stable. The package directory uses the suggested slug with the execution
date prepended, for example
`docs/work-packages/YYYYMMDD-db01-backup-restore-baseline/`.

Packages in the same wave may run in parallel only when their dependency cells
allow it. A later-numbered package may be scaffolded for design review, but it
may not claim execution evidence that depends on an incomplete predecessor.

### Campaign gates

| Gate | Requirement |
| --- | --- |
| S0 — Production safety | DB01–DB05 are complete before any watershed data release mutates production. |
| S1 — Contract freeze | DB06–DB10 are complete before release-ledger or reconciler schemas are treated as stable. |
| S2 — Clean-build proof | DB10A and DB11–DB21 can build and validate the same release twice from empty state, with runtime capability reads from materialized state, before reconciler implementation is accepted. |
| S3 — Reconciliation proof | DB21A–DB24 pass legacy-base, idempotency, failure, recovery, and exact rollback tests before deployment automation can activate data. |
| S4 — Deployment readiness | DB25–DB27A pass serialization, least-privilege, durable-execution, authorization-path, and compatible production schema/code rollout tests before a production data release is proposed. |
| S5 — Release readiness | DB28–DB32, including DB30A base adoption, produce and rehearse the exact accepted release before DB33 may be authorized. |

These gates supplement package dependencies; they do not grant production
authority. The minimum operational gates are:

| Operation | Required state and authority |
| --- | --- |
| Repository-only implementation | Listed package dependencies and repository mutation authority; no production implication. |
| Production read-only inspection | Explicit host/database read-only authority and evidence handling; no configuration or data mutation. |
| Runtime or container mutation | DB01 recovery evidence, DB02 lock and no-recreate contract, a reviewed rollback, and package-specific production authority. |
| Schema or application compatibility rollout | S0, DB25–DB27, fresh backup where required, shared lock, one-shot migrations, and explicit production authority. |
| Legacy baseline adoption | S0–S4, DB30A, a production-shaped adoption/rollback rehearsal, fresh verified off-host backup, and independent approval bound to exact baseline/capability hashes. |
| Watershed data activation | S0–S5, a fresh verified off-host backup, independent approval bound to exact hashes, and DB33 authority. |
| Restore, volume migration, or destructive recovery | DB01 restore proof, the host-wide lock, maintenance/quiescence, exact source/target identity, separately reviewed rollback, and operation-specific authority. |
| Legacy loader mutation | Rejected in production after DB04; an emergency recovery package cannot bypass base, lock, backup, and approval requirements. |

### Wave 0 — Make the current production service recoverable

#### DB01 — Backup and restore baseline

Suggested slug: `db01-backup-restore-baseline`

- **Depends on:** none.
- **Deliver:** turn the existing backup command into scheduled, encrypted,
  off-host backup with failure reporting; define separate time-based
  daily/weekly retention and release-point retention for the active plus two
  rollback releases; document maintenance entry/exit, disaster and selective
  restore, database-role recreation, and protected operational-account seeding.
- **Prove:** restore a retained backup into an isolated compatible PostGIS
  instance, run database and application smoke checks, and record duration,
  versions, checksums, counts, recovery-point age, and achieved RTO; test
  encryption-key recovery, a missed/stale timer, forced failure notification,
  reboot persistence, and controlled pruning. A successful dump alone is not
  completion evidence.
- **Decision closed here:** backup provider, key ownership, restore authority,
  whether the RPO must be shorter than 24 hours, and the maximum acceptable
  RTO. Provision restore capacity to that decision and terminate on hold when
  the drill exceeds it; merely recording an arbitrary duration is insufficient.

#### DB02 — Canonical production runtime bundle

Suggested slug: `db02-production-runtime-bundle`

- **Depends on:** none for repository work; DB01 before production mutation.
- **Deliver:** pin the currently running PostGIS version without upgrading it;
  define the safe interim and final canonical checkout, Compose project,
  `compose.prod.yml`, and systemd unit set; specify a no-`down`, no-database-
  recreate adoption path; inventory and remove or loopback-bind every internal
  published port; and require mode-`0600` minimized environment files.
- **Deliver:** define one absolute host-wide lock and its ownership/permissions
  for application deploy, migration, data activation, scheduled and on-demand
  backup, restore, volume work, recovery, and legacy mutation. Specify shared
  versus exclusive modes or an inherited token so an orchestrator can invoke a
  backup without deadlocking on its own lock.
- **Prove:** render and inspect the production Compose configuration and its
  proposed actions; fail if the database would be created or recreated;
  exercise the lock, unit, cancellation, nested, and contention contracts in
  isolated fixtures; freeze actual operator/systemd/CI identities and current
  socket reachability from localhost, Tailscale, Compose peers, and the public
  interface; record observed host-firewall behavior; document rollback without
  unsafe stop semantics. Actual production lock/unit/reboot/rollback behavior
  is DB03 adoption evidence.
- **Boundary:** this package creates the repository-owned runtime contract; it
  does not silently apply it to `wepp3`.

#### DB03 — Production runtime convergence

Suggested slug: `db03-production-runtime-convergence`

- **Depends on:** DB01, DB02.
- **Deliver:** stabilize `wepp3` without switching Compose project or invoking
  the loaded legacy `ExecStop`; record container/image/volume IDs, neutralize
  unsafe stop behavior without triggering it, adopt the host-wide lock and
  hardened sockets/secrets, and restart only application services. Final
  Compose-project and systemd convergence occurs with DB05 when the database
  has an explicit named-volume target.
- **Prove:** inspect the proposed Compose action and fail on database recreate;
  capture before/after Compose, unit, container, image, and volume identity;
  demonstrate cross-principal mutual exclusion; run smoke checks; verify the
  original database container and volume remain attached; exercise the
  no-recreate rollback; and complete a successful scheduled off-host backup
  cycle under the adopted lock afterward.
- **Authority:** production mutation must be explicit in the scaffolded
  package; repository implementation approval is insufficient.

#### DB03A — Production runner ownership closure

Suggested slug: `db03a-production-runner-ownership-closure`

- **Depends on:** DB03 host convergence and the reviewed safe branch.
- **Deliver:** fast-forward the fork's `main`; configure the existing protected
  production runtime as the fork's Actions secret without exposing values;
  register a new `rogerlew`-owned `wepp3` runner in a separate installation;
  keep the old upstream runner disabled.
- **Prove:** exact workflow content, no queued/in-progress jobs, verified runner
  release digest, expected service user/group/labels, GitHub online/idle state,
  old runner disabled state, and unchanged DB03 runtime/database invariants.
- **Boundary:** do not dispatch a workflow or change the production runtime,
  application, database, backup, firewall, or data.

#### DB04 — Legacy loader and observability guardrails

Suggested slug: `db04-legacy-loader-guardrails`

- **Depends on:** DB02; production deployment follows completed DB03/DB03A.
- **Deliver:** prohibit destructive legacy loader modes in production,
  especially `load_watershed_data --force` and `--force --runids`; make unsafe
  combinations fail closed; establish Silk retention or disable unnecessary
  response capture; correct operational guidance and tests.
- **Prove:** automated tests cover environment detection, every destructive
  flag combination, non-production behavior, and retention behavior; a
  production-configured container rejects destructive loader execution before
  deletion begins.

#### DB05 — Named PostgreSQL volume cutover

Suggested slug: `db05-named-postgres-volume-cutover`

- **Depends on:** DB01, completed DB03/DB03A, and DB04.
- **Deliver:** enter maintenance mode and prove write quiescence; record exact
  container, image, and source-volume IDs; create and verify a fresh encrypted
  off-host backup; migrate the anonymous production volume to the named volume
  using the pinned version; finish canonical Compose/systemd convergence; and
  retain the source through a stable reference that cannot be lost to an
  ordinary volume prune.
- **Prove:** restore and migration checks cover roles, extensions, migrations,
  sequences, release state, schema, watershed and non-watershed counts and
  checksums, and application behavior; actually exercise rollback; verify
  restart and host reboot persistence; complete and restore-test a post-cutover
  scheduled off-host backup; prohibit prune; and leave old-volume deletion to
  a new separately authorized package after the rollback window.

#### DB05A — Retire the held anonymous volume

Suggested slug: `db05a-retire-anonymous-volume`

- **Depends on:** DB05 complete, its rollback window closed by recorded
  authority, and a successful post-cutover backup restore test.
- **Deliver:** re-identify the held source by recorded container/volume ID,
  prove no running or rollback configuration references it, preserve the DB05
  cutover/rollback evidence off-host, and delete only that exact volume under
  the host-wide lock.
- **Prove:** the named production volume and scheduled backups remain healthy,
  restart and application smoke checks pass, no unrelated volume is removed,
  and the administration log records approver, operator, exact deleted ID, and
  final backup/restore evidence. This cleanup is not part of S0 and may remain
  pending while the rollback window is open.

### Wave 1 — Freeze identity, release, plan, and storage contracts

#### DB06 — Domain ownership and identity audit

Suggested slug: `db06-domain-identity-audit`

- **Depends on:** none; use production read-only access only when authorized.
- **Deliver:** enumerate watershed-owned versus persistent tables, foreign-key
  and deletion boundaries, public identifiers, batch/member identities,
  Parquet joins, current uniqueness, row counts, schema signature inputs, and
  compatibility consumers in the API and client.
- **Prove:** tests or read-only queries substantiate every proposed business
  key; ambiguities and dirty data become explicit blockers rather than inferred
  constraints.

#### DB07 — Stable identity and metadata authority contract

Suggested slug: `db07-identity-metadata-contract`

- **Depends on:** DB06.
- **Deliver:** decide immutable `collection_key` and `watershed_key` naming,
  replaceable run IDs, child business keys, split/merge/replacement lineage,
  route compatibility, and the field-by-field metadata and geometry precedence
  matrix for every current collection.
- **Prove:** worked fixtures cover retained, renamed, replaced, split, merged,
  metadata-only, geometry-only, and deliberately removed watersheds; every
  conflict resolves deterministically or fails preparation.

#### DB08 — Versioned release and index schemas

Suggested slug: `db08-release-index-schemas`

- **Depends on:** DB07.
- **Deliver:** versioned, machine-validated schemas and representative fixtures
  for the release manifest, exact batch-member index, artifact reference,
  transformation lineage, RHESSys capability index, validation report, and
  compatibility envelope. Authentication fields contain secret references
  only; credentials and credential-bearing URLs are schema-invalid.
- **Prove:** positive and negative fixtures validate in CI; schemas reject
  duplicate logical identity, wildcard removals, mutable unverified inputs,
  missing required capability assets, and incompatible contract versions.

#### DB09 — Fingerprint and base-specific plan contract

Suggested slug: `db09-fingerprint-plan-contract`

- **Depends on:** DB08.
- **Deliver:** canonical serialization and versioned fingerprints for artifacts,
  runs, capabilities, watershed-domain state, and releases; schemas for
  forward, exact-inverse, and empty-build plans keyed by explicit base,
  target, schema, data contract, materializer digest, and fingerprint version.
- **Prove:** golden fixtures are stable across repeated processes; semantic
  changes alter the intended fingerprint; ordering and irrelevant formatting
  do not; plans cannot be replayed against a different base.

#### DB10 — Durable artifact-store contract

Suggested slug: `db10-artifact-store-contract`

- **Depends on:** DB08.
- **Deliver:** define the operator-owned `forest1:/wc1` artifact backup root,
  private filesystem ownership, content-addressed key layout, retained-release
  policy, manual cleanup, cache behavior, and recovery responsibilities.
- **Prove:** threat and failure review covers partial copy, hash collision,
  corrupt backup, accidental deletion, storage exhaustion, forest1
  unavailability, and restoration of the active plus two rollback releases;
  record licensing, sensitivity, residency, and retention constraints for every
  artifact class.

#### DB10A — Artifact-store infrastructure acceptance

Suggested slug: `db10a-artifact-store-infrastructure`

- **Depends on:** DB10.
- **Deliver:** provision private test and production directories at
  `forest1:/wc1/utility-watershed-analytics-artifacts/v1`, with verified atomic
  copies, capacity preflight, deterministic inventory, retention, and restore
  behavior. Keep database backups separate.
- **Prove:** the real path passes three-release copy and exact clean restore,
  idempotent rerun, private-mode checks, partial/conflicting/corrupt copy and
  missing-object rejection, unavailable-path failure, and the 100 GiB
  free-space floor.
- **Authority:** the operator's explicit forest1 decision controls this package;
  no paid provider or external storage account is authorized.

### Wave 2 — Build immutable inputs into an empty database

#### DB11 — Release-tool CLI and reproducible image

Suggested slug: `db11-release-tool-foundation`

- **Depends on:** DB08, DB09.
- **Deliver:** a tested command framework for `prepare`, `validate`, `plan`,
  `build`, `apply`, `rollback`, `recover`, and `status`; stable exit codes and
  structured logs; and a repository-root, code-and-toolchain-only image built
  before manifests and plans reference its digest.
- **Prove:** the image contains no release manifests, plans, secrets, or source
  data; a digest-pinned invocation consumes verified read-only inputs; CLI
  errors are fatal and machine distinguishable.

#### DB12 — Content-addressed artifact client and cache

Suggested slug: `db12-artifact-client-cache`

- **Depends on:** DB10A, DB11.
- **Deliver:** streaming publish, fetch, checksum verification, atomic cache
  promotion, cache corruption recovery, immutable lookup, and bounded cleanup
  for all release artifacts.
- **Prove:** integration tests exercise interrupted transfer, wrong checksum,
  existing corrupt cache entries, concurrent fetches, missing objects,
  permission denial, store conflict, retained/leased cache protection, absence
  of a store-delete API, and the accepted test/production filesystem boundary.
  Credential rotation and cloud roles do not apply to the operator-authorized
  local forest1 design.

#### DB13 — Stable watershed identity migration

Suggested slug: `db13-watershed-identity-migration`

- **Depends on:** DB07, DB06 evidence.
- **Deliver:** choose and implement the relational shape that separates an
  immutable internal/logical watershed identity from the current replaceable
  source run revision; add aliases/redirects decided by DB07; migrate child
  foreign keys through an expand, backfill, dual-compatible, validate, and
  later contract sequence; preserve run-ID routes and feature IDs during the
  compatibility window.
- **Prove:** migrate a production-shaped snapshot forward, run old/new code at
  the documented compatibility points, reject duplicate keys, and use a run-
  replacement fixture to preserve watershed relational identity, child feature
  IDs, and the supported old/new routes; prove the rollback boundary without
  delete/reinsert semantics.

#### DB14 — Watershed-domain integrity constraints

Suggested slug: `db14-domain-integrity-constraints`

- **Depends on:** DB06, DB13.
- **Deliver:** database and model constraints for accepted watershed, batch,
  subcatchment, channel, soil, land-use, and join identities; make table
  ownership and cascade behavior explicit.
- **Prove:** production-shaped data satisfies the constraints; duplicate and
  orphan fixtures fail; migration locking and duration are measured; auth,
  session, and other non-watershed tables remain outside the rebuild boundary.

#### DB15 — Release ledger and capability-serving schema

Suggested slug: `db15-release-ledger-capabilities`

- **Depends on:** DB08, DB09, DB13.
- **Deliver:** migrations and models for immutable release records, the
  singleton `ActiveDataRelease` initialized in `EMPTY`, attempts and leases,
  per-run state, artifact lineage, and atomically activated `RunCapability`
  rows with durable URI and immutable index references.
- **Prove:** model and migration tests cover first activation, retained
  history, state transitions, uniqueness, expired leases, incompatible
  releases, sanitized failure summaries, operator/workflow attribution, and
  capability visibility tied to the active release.

#### DB16 — Attempt-scoped staging and recovery schema

Suggested slug: `db16-staging-recovery-schema`

- **Depends on:** DB14, DB15.
- **Deliver:** fixed migration-created staging tables keyed by attempt, bounded
  loading paths, staging constraints and indexes, owner/heartbeat/expiry,
  space preflight including artifact, staging, index, backup, and WAL margins,
  and recovery cleanup semantics for every non-terminal state.
- **Prove:** concurrent-attempt rejection, crash/expiry recovery, bounded-memory
  loading, disk preflight failure, cleanup retry, and preservation of active
  serving tables are covered by integration tests.

#### DB17 — Strict source resolution and exact member indexes

Suggested slug: `db17-source-resolution-indexes`

- **Depends on:** DB08, DB11, DB12.
- **Deliver:** standalone and batch source adapters that resolve mutable
  upstream discovery during preparation only, freeze exact run membership and
  source metadata, publish immutable artifacts, and make every required fetch
  or parse failure fatal.
- **Prove:** fixtures cover empty upstream results, missing members, duplicate
  IDs, custom master filenames, membership drift, partial download, malformed
  GeoJSON/Parquet, and repeat preparation from cached immutable inputs.

#### DB18 — Deterministic NASA 202606 enrichment

Suggested slug: `db18-nasa-202606-enrichment`

- **Depends on:** DB07, DB12, DB17.
- **Deliver:** implement the inventory's merge contract for
  `batch;;nasa-roses-202606-psbs`, preserving target run IDs and geometry while
  adding the approved attributes from the locked source artifact with explicit
  join keys, precedence, provenance, and checksums.
- **Prove:** positive, missing-key, duplicate-key, conflicting-value,
  geometry-change, and member-count fixtures; repeated execution produces the
  same bytes and fingerprints.

#### DB19 — RHESSys vendor, index, and validation tooling

Suggested slug: `db19-rhessys-artifact-tooling`

- **Depends on:** DB08, DB12, DB17.
- **Deliver:** tools for dynamic Parquet/spatial-input and precomputed GeoTIFF
  capability modes, durable copying, immutable indexes, structural validation,
  scenario/variable metadata, CRS and geometry compatibility, and representative
  sample reads.
- **Prove:** fixtures cover missing and partial scenarios, renamed variables,
  Parquet schema drift, corrupt GeoTIFFs, CRS mismatch, geometry revision
  mismatch, interrupted upload, and capability removal.

#### DB19A — Materialized capability runtime integration

Suggested slug: `db19a-capability-runtime-integration`

- **Depends on:** DB15, DB19.
- **Deliver:** make server RHESSys and release-declared SBS endpoints resolve
  eligibility, mode, durable base URI, immutable index and checksum, scenarios,
  variables, geometry revision, and access policy from the active
  `RunCapability` state; expose that capability metadata to the client; remove
  hard-coded run/scenario lists and run-ID-derived WEPPcloud URL conventions.
- **Deliver:** define dual-compatible behavior while `ActiveDataRelease` is
  still `EMPTY` for the production schema rollout. Only in `EMPTY`, an exact
  allowlisted, observable legacy fallback may retain the current upstream
  probes; it is disabled atomically by DB30A adoption. Runtime probing in
  `ACTIVE` may report health but cannot create intended capability.
- **Prove:** the `EMPTY` allowlist preserves only reviewed current behavior and
  emits fallback telemetry; after the state becomes `ACTIVE`, absent or
  disabled capability rows do not probe upstream or expose features. Catalog,
  tile, geometry, dynamic Parquet/query, and SBS paths read declared durable
  indexed assets; checksum/geometry/index mismatch fails closed; client
  eligibility and scenarios come from the API; TTL-managed upstream
  unavailability does not break an accepted durable capability. Tests exercise
  both sides of the atomic adoption transition.

### Wave 3 — Reconcile an existing database atomically

#### DB22 — Base-aware planner and exact inverse

Suggested slug: `db22-base-aware-planner`

- **Depends on:** DB09, DB15, DB21, DB21A.
- **Deliver:** inspect the active base, assert compatibility, compare canonical
  identities and fingerprints, classify exact adds/updates/removals/unchanged
  state, generate forward and exact-inverse plans, and generate an empty-build
  plan independently.
- **Prove:** fixtures cover metadata-only and geometry changes, run replacement,
  batch shrink/expansion, capability changes, unexpected large removals,
  unknown active base, changed materializer/schema, and deterministic plans.

#### DB23 — Atomic desired-state reconciler

Suggested slug: `db23-atomic-reconciler`

- **Depends on:** DB16, DB22.
- **Deliver:** activation that reasserts the base, locks the active-release row
  and transaction advisory lock, validates attempt staging, upserts retained
  identities in place, regenerates simplified geometry when its source changes,
  deletes only exact reviewed state, atomically replaces capability-serving
  rows, advances the active pointer, and records results. It must reuse DB20's
  canonical staged rows and mutation primitives, extending them for non-empty
  bases rather than implementing a second writer.
- **Prove:** retained watershed and child public identities remain stable;
  exact removals do not affect unrelated runs; readers see old or new accepted
  state rather than a partial mixture; non-watershed application state is
  unchanged.

#### DB24 — Idempotency, failure, recovery, and rollback proof

Suggested slug: `db24-reconciler-resilience`

- **Depends on:** DB23.
- **Deliver:** an integration fault matrix and recovery commands covering every
  preparation, staging, locking, activation, post-activation, and rollback
  boundary; exact rollback asserts the failed target is currently active.
- **Prove:** applying an active release produces zero domain/capability changes;
  missing sources and pre-activation failures preserve the prior release;
  expired attempts recover; injected activation failures roll back; the exact
  inverse restores the prior fingerprint; disaster rebuild reaches the same
  accepted state; and clean build versus reconciliation to the same target
  produce identical domain and capability fingerprints.
- **Prove the no-op boundary:** the active pointer and activation timestamp,
  serving rows, and immutable artifacts remain unchanged; only documented
  audit/report records may append. The later orchestrator must not create a
  backup for an already-active verified no-op.

### Wave 4 — Integrate controlled deployment

#### DB25 — Code/data compatibility and deployment serialization

Suggested slug: `db25-deployment-serialization`

- **Depends on:** DB03, DB24.
- **Deliver:** one GitHub production concurrency group and one canonical host
  lock shared by code, schema, and data operations; explicit one-shot
  migrations; compatibility checks for code, schema, contract, materializer,
  artifacts, capabilities, and active base.
- **Deliver:** least-privilege database roles and separately delivered,
  rotatable credentials for planner/status reads, staging writes, activation,
  application runtime, backup, migration, and restore/break-glass operations;
  document which transaction steps require elevation and prevent ordinary
  application or preparation roles from bypassing the reconciler.
- **Prove:** competing code/data jobs serialize at both layers; stale reviewed
  plans, incompatible migrations, wrong image digests, and lock loss fail
  before activation; normal application container startup does not race or
  implicitly run production migrations; negative permission tests and
  credential rotation cover every role and emergency elevation is audited.

#### DB26 — Production database deployment orchestrator

Suggested slug: `db26-deploy-database-orchestrator`

- **Depends on:** DB01, DB24, DB25.
- **Deliver:** `scripts/deploy_database.sh` and its durable non-interactive
  execution unit, covering secrets, digest-pinned tool launch, preflight,
  verified off-host backup, reviewed plan/base/hash confirmation, apply, smoke
  checks, report persistence, failure recovery, exact rollback, and cleanup.
- **Prove:** staging exercises success, interruption, lost client session,
  failed backup, stale base, failed smoke test, no-op apply, rollback, process
  crash, and host reboot; logs and final status remain available without a
  persistent SSH or tmux session.
- **Prove durable-unit semantics:** use an explicit principal and oneshot or
  equivalent no-blind-restart policy; define signals and timeouts; detect and
  recover nonterminal attempts before resume; invalidate discovery caches or
  restart affected workers after activation; store mode/ownership-controlled,
  secret-scanned logs and reports, copy required reports off-host, enforce
  retention, and alert on failed, stale, or abandoned attempts. An already-
  active verified no-op takes no backup and rewrites no serving state.

#### DB27 — Protected release workflow, roles, and status

Suggested slug: `db27-protected-release-workflow`

- **Depends on:** DB26.
- **Deliver:** CI preparation and clean-build validation, immutable release
  artifacts and reports, protected manual production deployment, separation of
  preparer/approver/deployer/rollback roles, active-release status, and
  inventory-snapshot reconciliation; monitor active-release mismatch, storage
  capacity/growth, artifact and backup age, and failed attempts. Merging a PR
  does not deploy data.
- **Prove:** permission tests and a staging rehearsal show that unapproved or
  mutable inputs cannot deploy, approvals bind exact hashes, reports survive
  failed jobs, active status matches the database, and rollback remains a
  distinct protected action.

#### DB27A — Production compatibility schema and code rollout

Suggested slug: `db27a-production-compatibility-rollout`

- **Depends on:** S0, DB19A, DB25, DB26, DB27, and explicit production
  schema/application mutation authority.
- **Deliver:** under the shared host lock and a fresh verified backup, run the
  additive one-shot DB13–DB16 migrations and deploy dual-compatible application
  code, including bounded `EMPTY`-ledger capability behavior, before any base
  adoption or data activation.
- **Prove:** current watershed and non-watershed data, public identities, API
  behavior, and observed legacy capabilities remain unchanged; migration locks
  and duration fit the accepted budget; schema signatures and database roles
  match; ordinary application startup cannot race or implicitly substitute for
  the migration; the rollback/roll-forward boundary is recorded and rehearsed
  on a production-shaped copy.
- **Authority:** this is the first production schema/code mutation in the
  campaign and needs its own approver/operator/rollback assignment; DB27's
  workflow-role design is not authorization by itself.

### Wave 5 — Prepare and activate the first authoritative release

#### DB28 — Gate Creek and Victoria locked release inputs

Suggested slug: `db28-gate-victoria-release-inputs`

- **Depends on:** DB19.
- **Deliver:** freeze exact Victoria membership and publish immutable Gate
  Creek and Victoria boundary, subcatchment, channel, soil, land-use, hillslope,
  and other required ordinary release inputs; copy and index accepted Gate
  Creek dynamic RHESSys inputs/outputs plus verified Sooke09 and Sooke15 map
  products into durable project storage. Do not infer capability for other
  Victoria members.
- **Prove:** source and destination checksums, immutable indexes, structural
  validation, exact member/count/join checks, representative sample reads,
  clean preparation without upstream access, and retention protection satisfy
  the inventory, release, and capability contracts.

#### DB29 — Mill Creek re-vendoring

Suggested slug: `db29-mill-creek-rhessys-revendor`

- **Depends on:** DB19.
- **Deliver:** publish every ordinary watershed input required to build
  `some-oligopoly`, re-vendor its spatial and precomputed RHESSys map assets
  durably, build its immutable capability index, and establish explicit lineage
  from `mdobre-invincible-scarab` without relying on the deleted source.
- **Prove:** every acceptance criterion in the inventory passes, including
  catalog and representative map reads; former Mill Creek remains untouched in
  production until the successor watershed and capability are release-ready.

#### DB30 — NASA successor and Bremerton locked inputs

Suggested slug: `db30-nasa-bremerton-inputs`

- **Depends on:** DB18, DB21.
- **Deliver:** prepare the enriched exact member index and immutable artifacts
  for `nasa-roses-202606-psbs`, plus validated exact membership and artifacts
  for `bremerton-2026-psbs`; record all approved exclusions and metadata.
- **Prove:** counts, identities, geometries, checksums, enrichment lineage,
  expected Parquet joins, and negative membership-drift tests pass from the
  durable artifacts without upstream access.

#### DB30A — Production legacy-base capture and adoption

Suggested slug: `db30a-production-legacy-base-adoption`

- **Depends on:** DB01, DB10A, DB21A, DB27A, DB28, and explicit production
  release-metadata/capability mutation authority.
- **Deliver:** under the shared lock and after a fresh verified encrypted
  off-host backup, capture exact current production membership and canonical
  normalized watershed-domain rows as immutable artifacts; assign the reviewed
  stable identities; produce and retain the legacy baseline manifest,
  fingerprint, rebuild report, and source-independent artifacts needed for the
  first inverse, including old NASA and former Mill Creek; materialize any
  retained legacy capabilities only from accepted durable indexed assets; then
  register that baseline as active without changing watershed-domain rows.
- **Prove:** rebuild the captured baseline in staging to the same fingerprint;
  rehearse adoption, post-commit capability/API verification, rollback to
  `EMPTY` plus fallback, and adoption again on a production-shaped copy before
  production mutation. Production adoption rechecks `ActiveDataRelease=EMPTY`,
  populated serving state, schema, contracts, and reviewed fingerprint
  atomically; watershed-domain rows and non-watershed state are unchanged;
  public capability behavior remains equivalent when new capability rows
  replace legacy probing with already verified durable assets; those rows are
  part of the reviewed baseline fingerprint; all artifacts are retained and
  restore-tested. A failed post-commit check invokes the rehearsed rollback and
  re-verifies the unchanged watershed and non-watershed fingerprints.
- **Failure rule:** any mismatch rolls back the ledger and reviewed capability
  bootstrap together, leaves the ledger `EMPTY`, and leaves all pre-existing
  rows untouched. If exact source-independent rollback artifacts cannot be
  produced, terminate on hold rather than substituting backup-only rollback
  silently.

#### DB31 — First target manifest and clean build

Suggested slug: `db31-first-release-candidate`

- **Depends on:** DB21, DB22, DB28, DB29, DB30, DB30A.
- **Deliver:** the complete desired-state manifest retaining Gate Creek and
  Victoria, replacing Mill Creek with `some-oligopoly`, replacing
  `nasa-roses-2026-sbs` with `nasa-roses-202606-psbs`, adding Bremerton, and
  declaring only verified RHESSys capabilities.
- **Prove:** exact reviewed adds, updates, replacements, and removals match the
  inventory; empty-build CI passes twice with identical fingerprints; the
  forward and exact-inverse plans bind the adopted legacy manifest and
  fingerprint; the empty plan is independently keyed; all plans and the
  validation report are retained by hash.

#### DB32 — Full staging deployment rehearsal

Suggested slug: `db32-staging-release-rehearsal`

- **Depends on:** DB27, DB27A, DB31.
- **Deliver:** define and create a production-shaped staging copy with recorded
  snapshot age and base fingerprint, exact PostgreSQL/PostGIS/GDAL/code/schema
  versions, production-scale rows and geometry, disk/WAL margin, worker
  concurrency, and network shape; document every deviation. Restore through a
  controlled path, preserve relational shape while masking sensitive user data,
  use no production credentials, restrict access, and destroy the copy on its
  recorded retention schedule.
- **Deliver:** deploy the exact release candidate through the protected path,
  measure preparation/staging/lock time and API latency, exercise the inverse
  rollback, then deploy forward again. Production-base drift that changes the
  plan invalidates approval and requires a new plan and rehearsal disposition.
- **Prove:** every architecture acceptance criterion passes; retained public
  identities and non-watershed state survive; reports and active status agree;
  rollback returns the prior fingerprint; measurements disposition whether
  blue-green activation remains deferred.

#### DB33 — First production release activation

Suggested slug: `db33-first-production-release`

- **Depends on:** S0, DB32, distinct approval and explicit production mutation
  authority.
- **Deliver:** after final preflight/staging and immediately before activation,
  create a fresh backup, complete and verify its encrypted off-host copy, and
  record its maximum age and artifact hash; verify the reviewed base-specific
  plan; activate the exact rehearsed release by immutable hashes; run smoke and
  capability checks; retain the prior release and inverse plan; and reconcile
  the production inventory snapshot and administration log. The ordinary
  scheduled backup cannot satisfy this activation gate.
- **Prove:** production active-release identity and fingerprint match the
  approved candidate; target dataset membership and capabilities match the
  inventory; old NASA and former Mill Creek are absent only after successors
  pass; rollback readiness and retention are independently confirmed.

The authoritative target membership and dataset-specific acceptance details
remain in the [database inventory](database-inventory.md). Package execution
must not weaken the implementation and safety contract in the architecture.

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

Unresolved decisions have an owning package. That package must either close the
decision with recorded authority or terminate on hold; a downstream package
must not silently choose a value.

| Decision | Owning package |
| --- | --- |
| Backup provider, key ownership, restore authority, final RPO, and maximum acceptable RTO | DB01 |
| Watershed-key names and future public-route migration policy | DB07 |
| Field-level metadata and geometry precedence for every collection | DB07 |
| Artifact backup host, root, ownership, integrity, and retention | DB10 |
| Prepare, approve, deploy, and rollback roles and separation | DB27 |
| Activation lock-time and API-latency budget for blue-green escalation | DB32 |

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
