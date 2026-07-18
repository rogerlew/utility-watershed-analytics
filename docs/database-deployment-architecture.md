# Database Deployment Architecture and Tooling Specification

Status: Proposed

Last updated: 2026-07-16

Related documents:

- [Forward roadmap](ROADMAP.md)
- [Roadmap dual-review disposition](database-deployment-roadmap-review.md)
- [Work-package governance and catalog](work-packages/README.md)
- [Production database and data-source inventory](database-inventory.md)
- [Independent review disposition](database-deployment-architecture-review.md)
- [Deployment guide](../DEPLOYMENT.md)

## 1. Summary

Watershed data should be deployed as a versioned declaration of desired state,
not as a sequence of production patches and not by discovering mutable upstream
state during deployment.

Each data release will lock:

- the exact watershed run IDs that should exist;
- immutable source artifacts and their checksums;
- deterministic enrichment or conversion lineage;
- expected database record counts and validation rules;
- declared RHESSys capabilities and required external assets; and
- the code and database-schema contract needed to materialize the release.

A strict release tool will prepare and validate all data before modifying the
serving tables. It will then reconcile the watershed-owned tables in one atomic
operation. Applying the same release again must produce no changes. The same
release must also be capable of building the watershed tables in an empty
database.

The production PostgreSQL volume should be named and persistent even though the
watershed dataset is reconstructible. Replaceability must be an explicit,
tested property of the build process rather than an accidental consequence of
an anonymous Docker volume.

## 2. Motivation and current limitations

The current deployment has useful components, but they do not form a database
build system:

- the GitHub deployment workflow rebuilds the application and runs Django
  migrations, but it does not deploy watershed data;
- `load_watershed_data` refuses to run against a populated database unless
  `--force` is supplied;
- `--force` deletes all watershed data in a transaction that commits before
  the replacement load starts;
- batch and child records are inserted rather than reconciled;
- individual source failures can be logged and ignored, allowing a partial
  load to commit;
- `--dry-run` does not fetch, parse, compare, or validate input data;
- downloaded files are considered current whenever a matching filename
  exists, with no checksum or source-version validation;
- production deployment does not record which source revisions produced the
  active rows; and
- PostgreSQL uses an anonymous Docker volume while the data cache uses a named
  volume.

These behaviors cannot reliably support deletion, metadata correction, batch
replacement, repeated deployment, or recovery from a partially failed load.

## 3. Goals

The proposed system must:

1. Materialize the same watershed state from the same release inputs every
   time.
2. Build from an empty database and reconcile an existing database using the
   same release definition.
3. Represent additions, updates, replacements, and removals explicitly.
4. Validate every required input before changing serving data.
5. Fail the release when any required watershed or artifact fails.
6. Preserve the previously active watershed state when a release fails.
7. Produce a reviewable plan before applying destructive changes.
8. Record artifact lineage, release identity, counts, code revision, and
   validation results.
9. Separate schema evolution from data-state evolution while checking their
   compatibility.
10. Make external RHESSys availability explicit rather than inferring it from
    the existence of a PostgreSQL watershed row.
11. Support rollback to the previous accepted data release.
12. Work without storing large GeoJSON, Parquet, or GeoTIFF files in Git.

## 4. Non-goals

The first implementation will not:

- use PostgreSQL as the durable archive for RHESSys source files;
- replay a growing history of one-off data patches to construct current state;
- deploy directly from a mutable upstream batch response;
- silently accept unavailable optional data when the release declares it
  required;
- make all application deployments automatically perform a data deployment;
  or
- initially require blue-green replacement of the entire PostgreSQL cluster.

Blue-green database deployment remains a possible later optimization. The
initial reconciler is designed to preserve Django authentication and other
non-watershed tables while still proving that watershed data can be rebuilt
from nothing.

## 5. Terminology

| Term | Meaning |
| --- | --- |
| Data release | An immutable declaration of the complete desired watershed inventory and its locked inputs. |
| Release manifest | The reviewed, tracked release file containing intent, exact dataset membership, validation policy, and artifact references. |
| Artifact | A GeoJSON, Parquet, GeoTIFF, or index file identified by content checksum and stored outside Git. |
| Preparation | Resolving upstream sources, transforming or enriching data, publishing immutable artifacts, and generating a release plan. |
| Build | Materializing a data release into empty watershed tables. |
| Reconciliation | Converging existing watershed tables to exactly match a data release. |
| Deployment | Backup, preflight, reconciliation, validation, activation, and reporting. |
| Collection key | A stable project-controlled identity for one logical source grouping across replaceable batch or standalone source revisions. |
| Watershed key | A mandatory stable project-controlled identity for exactly one logical watershed, distinct from its collection and replaceable upstream run ID. |
| Run ID | The current source-specific WEPPcloud identifier and source revision. It is also the existing database primary key and public route identifier. |
| Capability | A declared optional product family, such as RHESSys dynamic Parquets or precomputed map GeoTIFFs. |

## 6. Architectural principles

### 6.1 Desired state, not patch history

The active release contains the complete set of desired datasets. A run absent
from that set is a deletion candidate. A metadata or geometry change appears as
a changed artifact fingerprint. A replacement appears as one removed run and
one added run, with optional lineage metadata describing the relationship.

Database patches are reserved for:

- Django schema migrations;
- migrations of persistent, non-derived application state; and
- emergency corrections that are immediately incorporated back into the
  manifest or source artifact.

A manual database correction that is not represented in the release will be
lost on the next reconciliation and is therefore not an accepted steady state.

Idempotency applies to watershed-domain rows, capability serving rows, the
active-release pointer, and immutable artifacts: applying an already active
release changes none of them. Audit attempts, heartbeats, logs, and reports may
be appended and are excluded from the domain fingerprint.

### 6.2 Resolve upstream state before deployment

Preparation may inspect a WEPPcloud batch, enrich a master GeoJSON, and generate
an exact member index. Deployment consumes only the locked results of that
preparation.

This separation prevents an upstream removal, TTL deletion, schema change, or
temporary empty response from becoming an unintended production deletion.

### 6.3 Immutable and content-addressed inputs

Every required artifact must have a SHA-256 checksum and expected byte size.
Mutable URLs are permitted only as preparation inputs. Deployment artifacts
must be immutable or copied to a durable project-controlled location before
the release is accepted.

The local cache will be keyed by checksum, for example:

```text
/data/artifacts/sha256/be/be152890a843.../
```

Filename existence alone will never establish cache validity.

### 6.4 Strict before atomic

Network access, checksums, parsing, joins, schema checks, geometry checks, and
record construction occur before serving rows are changed. Reconciliation then
runs under a database advisory lock and a single transaction. Required source
errors are fatal.

### 6.5 Replaceable data, persistent service

The watershed tables are derived and must be clean-buildable. The serving
PostgreSQL instance should nevertheless use a named volume so routine container
lifecycle events cannot discard it. Rebuilds and cutovers must be explicit
operations with validation and rollback.

## 7. System overview

```text
 Mutable upstream sources                 Git repository
 (WEPPcloud, enrichment files)            (release manifest + code)
              |                                      |
              v                                      v
      release preparation -----------------> reviewable plan/diff
              |
              v
 Durable immutable artifact store
 (GeoJSON, Parquet, GeoTIFF, indexes)
              |
              v
     checksum-verified local cache
              |
              v
       staging + full validation
              |
              v
   atomic watershed reconciliation ------> build ledger/report
              |
              v
       serving PostGIS database ----------> Django API
```

RHESSys files remain outside PostgreSQL. The release declares where they live,
what products are supported, and what must be validated before a capability is
advertised by the application.

## 8. Release representation

### 8.1 Repository layout

The accepted DB08 layout and planned successor directories are:

```text
data-releases/
  schema/
    v1/
      artifact-reference.schema.json
      batch-member-index.schema.json
      compatibility-envelope.schema.json
      release-manifest.schema.json
      rhessys-capability-index.schema.json
      transformation-lineage.schema.json
      validation-report.schema.json
      plans/
        deployment-plan.schema.json
        forward-plan.schema.json
        exact-inverse-plan.schema.json
        empty-build-plan.schema.json
  fixtures/
    v1/
      cases.json
      valid/
      invalid/
  releases/
    2026-07-16.1/
      release.json
      batch-members.json
  plans/
    BASE_SHA--TARGET_SHA/
      MATERIALIZER_DIGEST/
        forward.json
        rollback.json
        empty-build.json
```

Large source artifacts are stored in durable object storage, not in this
directory. DB08 schemas and fixtures are tracked now; real releases, indexes,
and DB09 plans are added only by their successor packages.

### 8.2 Release manifest

DB08 formalizes the manifest and six supporting records in the
[version-1 release schema contract](database-release-schema-contract.md). A
manifest pins compatibility, exact collection membership and stable watershed
keys, exact expected removals, reviewed identity lineage, and immutable
validation evidence. Supporting indexes contain per-member artifacts, counts,
bounds, transformation lineage, and RHESSys capability details.

Every artifact location is HTTPS, credential-free, checksum-pinned, sized,
media-typed, and asserted verified. The checked-in examples under
`data-releases/fixtures/v1/` are illustrative contract proof, not real release
membership.

### 8.3 Base-specific deployment plans

A release manifest describes only target state. A deployment plan is derived
from a particular base state and is not intrinsic to the target release.

Plans are stored and reviewed separately, keyed by at least:

- base manifest SHA-256, or an explicit empty base;
- target manifest SHA-256;
- data-contract version;
- materializer image digest; and
- fingerprint-algorithm version.

DB09 freezes these coordinates and the exact action vocabulary in the
[fingerprint and plan contract](database-fingerprint-plan-contract.md). A
populated state pins release ID, exact manifest SHA-256, semantic release
fingerprint, and watershed-domain fingerprint. `EMPTY` is the only special base
and is restricted to reconstruction proof.

CI should produce three plans where applicable:

- a forward production plan from the expected active release;
- an exact inverse rollback plan from the target back to that base; and
- an empty-build plan used to prove reconstruction.

Every plan contains exact added, removed, and changed run IDs. Destructive
authorization cannot use globs. A large collection replacement may reference a
hashed exact removal-set artifact derived from the reviewed base manifest. The
apply transaction must assert that the active base release matches the plan;
otherwise it refuses to mutate the database.

The assertion compares the complete base state before artifact fetch or
staging. Exact inverse plans swap base and target, mirror before/after run state,
and negate row deltas; empty-build plans contain additions only and never
authorize clearing a populated database.

### 8.4 Exact batch membership

A batch release must lock the exact desired member run IDs. Deployment must
not rediscover them from the batch API.

Small batches may list members directly. Large batches should reference a
tracked or immutable batch index containing, for every member:

- canonical run ID;
- mandatory stable `watershed_key`;
- expected display metadata;
- boundary, subcatchment, channel, hillslope, soil, and land-use artifact
  references;
- independent hashes for metadata, geometry, and child datasets; and
- expected counts and geometry bounds.

Explicit membership gives watershed removal reviewable semantics. A preparation
report must show added, removed, retained, and changed members relative to the
currently active release.

### 8.5 Transformation and enrichment lineage

Deployment should consume the final transformed artifact rather than perform a
join against a mutable enrichment URL. The release records:

- every source artifact hash;
- transformation name and version;
- transformation code Git commit;
- configuration and join keys;
- output artifact hash;
- matched, unmatched, and duplicate counts; and
- validation report hash.

For the NASA successor batch, the new batch's run IDs and geometries remain
authoritative while approved metadata is joined from the WWS source. Historical
source run IDs must never overwrite successor run IDs.

### 8.6 RHESSys representation

RHESSys capability must be declared per mandatory watershed key and exact run
ID. The RHESSys index should describe:

- mode: `dynamic`, `precomputed`, or both;
- durable base URI;
- required scenarios;
- required geometry revisions;
- Parquet paths, schemas, spatial ID fields, variables, units, and year range;
- GeoTIFF paths, checksums, CRS, bounds, dimensions, band count, and nodata
  value;
- required spatial-input files; and
- whether each asset is required for release activation or optional.

The capability declaration must be materialized as serving database state in
the same activation transaction as the watershed rows. The application reads
the declared mode, durable base URI, index URI and hash, scenarios, and geometry
revisions from that state instead of hard-coded run ID sets or derived URL
conventions. Runtime probing may remain as a health check, but it does not
define intended capability.

### 8.7 Secrets

Manifests contain secret references, never credentials. For example:

```yaml
authentication:
  secret_ref: WEPPCLOUD_NASA_202606_TOKEN
```

The deployment environment resolves the reference. Tokens must not appear in
release plans, build reports, command lines, or database rows.

## 9. Database representation

### 9.1 Existing domain tables

The first implementation will continue to materialize:

- `watershed_watershed`;
- `watershed_subcatchment`; and
- `watershed_channel`.

It will also materialize a `RunCapability` model keyed by watershed and
capability type. A capability row contains the active mode, durable base URI,
immutable index URI and checksum, and the runtime configuration needed by the
API. RHESSys capability rows are replaced atomically with their corresponding
watershed release state. A fingerprint without serving configuration is not
sufficient.

Soil, land-use, and hillslope properties remain denormalized onto
`watershed_subcatchment` unless a separate schema change is approved.

Only these explicitly declared watershed-domain and capability tables are
owned by data reconciliation. Every other Django table is persistent by
default. Before any non-owned table is allowed to reference a reconciled row,
its stable identity, deletion behavior, and rollback semantics must be
specified; a data release must not cascade-delete user-owned state.

### 9.2 Release ledger

A Django migration should introduce a small release ledger. Proposed records:

#### `DataRelease`

- `release_id`, unique;
- manifest SHA-256;
- release schema version;
- data contract version;
- status: `validated`, `active`, or `superseded`;
- previous active release ID;
- aggregate expected and actual counts; and
- validation summary.

#### `ActiveDataRelease`

- a singleton row created by migration with state `EMPTY` and a nullable
  `DataRelease` pointer;
- state `ACTIVE` requires a non-null release pointer, while `EMPTY` is permitted
  only before the first activation or in an intentional clean-build database;
- active manifest hash and data-contract version; and
- activation timestamp.

The singleton constraint and a row lock provide the authoritative base-state
assertion during activation.

#### `DataReleaseAttempt`

- release and previous active release;
- application Git commit;
- operator or workflow run identity;
- status: `planning`, `staging`, `applying`, `succeeded`, `failed`, or
  `rolled_back`;
- started, validated, applied, and completed timestamps;
- reviewed and actual plan hashes;
- lease owner, heartbeat, and expiry timestamps;
- backup artifact identity;
- failure phase and sanitized error summary; and
- deployment report location or hash.

#### `DataRunState`

- release, collection key, and mandatory watershed key;
- canonical run ID;
- metadata fingerprint;
- watershed geometry fingerprint;
- subcatchment, channel, and Parquet input fingerprints;
- actual row counts;
- RHESSys capability fingerprint; and
- validation status.

The ledger is an audit and optimization aid, not the source of truth. The
tracked release manifest remains authoritative.

During the design and bootstrap phases, `docs/database-inventory.md` remains
the human-approved source of inventory decisions. Once Phase 1 is operational,
the accepted release manifest becomes the executable authority and the
inventory document should be generated from it or checked against it in CI.

DB09 specifies version-1 canonicalization in the
[fingerprint and plan contract](database-fingerprint-plan-contract.md). It
normalizes Unicode and exact decimals, sorts set-like records by stable
identity, fingerprints already canonical CRS-qualified geometry content, and
excludes database IDs, timestamps, attempts, and other volatile values. A
fingerprint-algorithm change requires a new fingerprint version and coordinated
data-contract review.

### 9.3 Integrity constraints

The reconciler should be supported by database constraints for identities that
are already assumed by the loader:

- one watershed per `runid`;
- one subcatchment per `(watershed_id, topazid)` for data-contract version 1;
- one channel per `(watershed_id, topazid, weppid, order)`.

Constraint introduction requires a duplicate audit and an explicit Django
migration. DB06's separately authorized aggregate production audit found zero
duplicate groups and zero child orphans for the proposed version-1 keys across
126 watersheds, 195,457 subcatchments, and 86,895 channels. That observation is
accepted migration input, not permanent enforcement. Because current Parquet
enrichment joins on `topazid`, every release must enforce exactly one matching
subcatchment and at most one authoritative Parquet row per
`(watershed, topazid)`. A future artifact that needs a different business key
requires a new data contract and join implementation rather than an implicit
fallback. The current ownership, key, join, and compatibility audit is
maintained in
[the DB06 domain identity audit](database-domain-identity-audit.md).

### 9.4 Stable logical identity

The existing public identity is the source run ID. Replacing a WEPPcloud run
therefore changes database primary keys, API URLs, bookmarks, and any future
foreign keys.

Every release member must have a stable `watershed_key`; every batch or
standalone source grouping has a separate `collection_key`. The model should
introduce `watershed_key` as a unique project-owned identity and treat upstream
run IDs as replaceable source revisions and compatibility aliases. Public-route
migration and redirects may be staged, but the identity must not remain
optional in the release schema.

Cases that need an explicit identity decision include:

- Mill Creek moving from `mdobre-invincible-scarab` to `some-oligopoly`;
- a batch member moving to another batch without changing watershed identity;
- one watershed splitting into multiple features; and
- multiple utilities sharing the same HUC10 geometry.

Replacement lineage is represented explicitly between watershed keys and
source revisions. Split and merge events list all predecessor and successor
watershed keys and require a reviewed routing and foreign-key migration plan.

DB07 freezes the version-1 decisions in the
[identity and metadata authority contract](database-identity-metadata-contract.md):
collection keys remain stable across source revisions; watershed keys remain
stable across rename, replacement, and collection moves; split and merge
successors receive new keys; retired keys are never reused; and historical run
IDs remain compatibility aliases. The DB08
[release schema contract](database-release-schema-contract.md) encodes those
decisions rather than deriving identity from source names or geometry.

## 10. Change semantics

| Change | Release representation | Reconciliation behavior |
| --- | --- | --- |
| Add a watershed | Add exact member and artifacts | Insert watershed and children after validation. |
| Remove a watershed | Omit member and declare expected removal | Delete children and watershed in the activation transaction. |
| Correct metadata | New master artifact or metadata fingerprint | Update only authoritative metadata fields. |
| Change watershed geometry | New geometry fingerprint | Update watershed geometry and regenerate simplified geometry. |
| Change subcatchments or channels | New child fingerprint | Upsert retained business identities, insert additions, and delete true removals while preserving public feature IDs. |
| Change soil, land use, or hillslope data | New Parquet fingerprint | Reapply mapped fields for that run, including authoritative nulls. |
| Add a batch | Add batch and exact member index | Insert validated members; no runtime discovery. |
| Replace a batch | Add successor and remove predecessor with lineage | Apply as reviewed additions/removals. |
| Replace a standalone run | Change source revision for stable watershed key | Insert the new revision and retire the old run ID while preserving logical lineage. |
| Add RHESSys data | Add capability and immutable asset index | Validate assets, then advertise capability. No PostgreSQL raster load. |
| Remove RHESSys data | Remove capability with expected change | Stop advertising it; retain or garbage-collect assets per policy. |
| Change model/schema | Django migration plus contract version | Deployment refuses incompatible code, schema, or data releases. |
| Emergency manual correction | Temporary audited patch plus immediate release-source correction | Next reconciliation enforces the corrected desired state. |

Metadata semantics must distinguish an absent property from an explicit null.
For fields declared authoritative by a release schema, absence is a validation
error; an explicit null clears the field. This prevents accidental retention of
stale metadata. The DB07 contract defines the field-by-field authority and
conflict matrix for every current collection; unresolved or unauthorized values
fail preparation.

## 11. Supported and anticipated cases

### 11.1 Known near-term changes

The design must support the following already identified work:

- replace Mill Creek `mdobre-invincible-scarab` with `some-oligopoly`;
- re-vendor and validate Mill Creek RHESSys products;
- retain Gate Creek `aversive-forestry` and its dynamic RHESSys products;
- retain the Victoria batch while declaring RHESSys only for verified members;
- replace `nasa-roses-2026-sbs` with `nasa-roses-202606-psbs`;
- deterministically enrich the NASA successor resources GeoJSON;
- remove selected watersheds from a batch;
- update watershed metadata without changing geometry or child records;
- add `bremerton-2026-psbs`; and
- add future batches and RHESSys products.

### 11.2 Additional cases

| Category | Cases the tooling must handle or reject safely |
| --- | --- |
| Upstream lifecycle | Run deleted by TTL, source temporarily unavailable, batch returns zero members, path changes, mutable file changes without a new name. |
| Identity | Run renamed, member moves between batches, duplicate run ID, case-only run ID change, logical watershed split or merge. |
| Metadata | Field added or renamed, value becomes null, duplicate enrichment key, unmatched enrichment row, conflicting sources, string exceeds model width. |
| Geometry | Invalid polygon, CRS missing or wrong, Polygon/MultiPolygon difference, empty geometry, large bounds shift, topology simplification change. |
| Children | Duplicate TOPAZ identities, child references unknown watershed, subcatchment count collapses unexpectedly, Parquet key has no matching subcatchment. |
| RHESSys | Scenario added or removed, variable renamed, Parquet schema changes, GeoTIFF CRS changes, geometry revision changes, only some assets upload successfully. |
| Deployment | Retry after interruption, concurrent deploy, disk exhaustion, long transaction, application traffic during activation, post-activation smoke-test failure. |
| Compatibility | New data requires code not deployed yet, code rollback cannot read new schema, migration changes field meaning, transform code changes with identical source bytes. |
| Operations | Restore from backup, redeploy previous release, cache garbage collection, forest1 storage unavailable, checksum mismatch. |
| Persistent state | Django users, sessions, admin logs, or future user-created records must survive watershed rebuilds and may reference stable watershed identities. |
| Reproducibility | GDAL, PostGIS, or transformation-library version changes output; timestamps or unordered iteration make artifacts nondeterministic. |

Unexpected large differences must fail closed. They must never be interpreted as
normal batch evolution merely because the upstream request succeeded.

## 12. Preparation workflow

Preparation converts mutable upstream information into a reviewable immutable
release.

A proposed operator interface is:

```bash
python manage.py data_release prepare \
  --base data-releases/releases/CURRENT/release.yaml \
  --descriptor data-releases/drafts/NEXT.yaml \
  --output data-releases/releases/NEXT
```

1. Build and publish the code/toolchain-only release-tool image, resolve its
   immutable digest, and exclude release manifests and plans from its contents.
2. Create a new release directory from the currently active release and record
   that resolved materializer digest.
3. Resolve configured upstream batches and standalone sources.
4. Download sources into temporary files, never directly over a trusted cache
   entry.
5. Validate transport status, file size, checksum, parseability, schemas, CRS,
   and basic geometry validity.
6. Apply deterministic enrichment and conversion steps.
7. Produce exact batch and RHESSys indexes.
8. Publish output artifacts to durable storage under immutable keys.
9. Re-download or otherwise verify the published bytes and hashes.
10. Generate a base-specific forward plan against the expected active release
   and its exact inverse rollback plan, showing:
   - datasets and run IDs added, removed, replaced, or retained;
   - metadata-only, geometry, child, and capability changes;
   - expected row-count deltas;
   - enrichment match and conflict reports; and
   - safety-threshold evaluation.
11. Commit the manifest and indexes plus the separately keyed plans for review.

Preparation may be rerun, but a published release ID is immutable. Any changed
target artifact requires a new release ID. A newly encountered base state
requires a new separately reviewed plan, not a mutation of the target release.

## 13. CI workflow

A data-release pull request should run:

1. manifest and index JSON Schema validation;
2. checksum and artifact-metadata verification;
3. deterministic transformation tests;
4. clean database creation with pinned PostgreSQL/PostGIS and GDAL versions;
5. Django migrations;
6. full watershed build from the proposed release;
7. database validation and API smoke tests;
8. a second application of the same release, which must report zero watershed
   changes;
9. watershed-domain fingerprint comparison before and after the second
   application, excluding audit-attempt timestamps;
10. upgrade testing from the currently active release; and
11. rollback-plan validation where schema compatibility permits.

Authenticated production artifacts may require a protected CI environment or a
deployment-time preflight. Lack of credentials must not convert required checks
into warnings.

DB08 implements the first gate for schemas and illustrative fixtures in
`.github/workflows/data-contract-ci.yml`. Later packages extend that workflow
with artifact access, materialization, fingerprint, smoke, and rollback gates
as those capabilities become executable.

## 14. Deployment workflow

Data deployment should initially be a protected, manually approved workflow
separate from ordinary application deployment. The workflow may later be
composed with application deployment after compatibility rules are proven.

The single operator-facing entry point is proposed as:

```bash
scripts/deploy_database.sh \
  --release data-releases/releases/2026-07-16.1/release.yaml \
  --plan data-releases/plans/BASE--TARGET/MATERIALIZER/forward.json \
  --expected-base BASE_MANIFEST_SHA
```

The wrapper is one long-lived host process holding the shared deployment lock.
It creates a durable database attempt/lease and passes the attempt ID and lease
token to each phase. Supporting commands remain available for preparation and
diagnosis, but they do not independently authorize production mutation:

```bash
python manage.py data_release plan RELEASE
python manage.py data_release fetch RELEASE
python manage.py data_release validate RELEASE
python manage.py data_release apply RELEASE \
  --attempt ATTEMPT_ID \
  --expected-base BASE_MANIFEST_SHA \
  --expected-plan-sha PLAN_SHA256
python manage.py data_release verify RELEASE
python manage.py data_release status
python manage.py data_release recover
```

The attempt lease is heartbeated during long phases and has an expiry. It
prevents a second conforming deploy from taking ownership after a process
crash. It is not a substitute for activation-time database locking and base
assertions.

Tooling responsibilities should remain separated:

- a tested Python package owns manifest parsing, hashing, transformations,
  staging, reconciliation, and validation;
- the Django management command exposes that package with database and settings
  integration;
- the shell script owns host checks, Docker invocation, locking, backup
  orchestration, and durable log/report paths; and
- the GitHub workflow owns CI, protected-environment approval, secret delivery,
  and publishing summaries.

Business rules must not be duplicated in shell or workflow YAML.

Production commands run in a one-off, code/toolchain-only release-tool image
built from the repository root and pinned by image digest. Release manifests
and plans are deliberately excluded from the image so they can reference its
already resolved digest without a self-referential build. Deployment mounts the
exact reviewed files read-only or fetches them by verified hash. The tool image
connects to the Compose network and mounts only those release files, the
content-addressed cache, staging/report paths, and required secrets. Deployment
must not depend on files being present in the long-running server container,
whose current build context contains only the `server` directory.

DB11 freezes the command names, JSON event envelope, exit codes, verified-input
behavior, reproducible build, and image content/runtime boundary in the
[release-tool foundation contract](database-release-tool-contract.md). Commands
owned by later packages fail explicitly until implemented.

The deployment sequence is:

1. Acquire the shared host deployment lock and verify the canonical checkout,
   Compose project, target environment, immutable tool-image digest, release
   and plan hashes, schema compatibility, free disk, and database health.
2. Create the deployment-attempt lease and assert the expected active base
   release.
3. Produce a fresh base-specific plan and require it to match the reviewed
   forward plan exactly.
4. Fetch all artifacts into the content-addressed cache.
5. Parse and stage the complete release without modifying serving rows.
6. Run all pre-activation validations and count comparisons.
7. Run and verify a production backup, including its required off-host copy,
   immediately before activation.
8. In one database transaction:
   - acquire a transaction-scoped PostgreSQL advisory lock;
   - lock the singleton `ActiveDataRelease` row with `SELECT ... FOR UPDATE`;
   - reassert the exact base manifest—or the explicit `EMPTY` state for a first
     activation—plus schema and materializer digest;
   - recompute the actual plan from staged and serving rows and compare its
     hash with the reviewed plan;
   - update the release-attempt record to `applying`;
   - upsert changed watershed rows;
   - reconcile changed child rows by stable business identity;
   - replace capability serving rows from the staged declarations;
   - delete explicitly expected obsolete runs;
   - regenerate simplified geometries where inputs changed;
   - record actual counts and fingerprints;
   - run final database invariants before commit; and
   - mark the new release active and the previous one superseded.
9. Run post-commit read checks and API smoke tests.
10. Invalidate application discovery caches or restart the affected workers.
11. Publish the deployment report and release identity.

If the requested release is already active and its fresh plan contains no
watershed-domain changes, deployment should record a successful no-op, run the
verification checks, and exit without taking another backup or rewriting rows.

The application may continue serving the previous committed data during
staging. The activation transaction should be kept short by doing parsing,
geometry normalization, and bulk staging beforehand.

### 14.1 Deployment serialization

Application, schema, and data deployments must share:

- one GitHub Actions concurrency group for production;
- one canonical host lock file;
- one canonical checkout and explicit Compose project name; and
- the same compatibility checks against the active data contract.

Application deployment should run migrations as an explicit one-shot step
before replacing workers and should deploy immutable image digests. It must not
rely solely on the server entrypoint's automatic `migrate`. Data deployment
rechecks the running schema and materializer digest immediately before
activation.

Once the reconciler is enabled, the legacy `load_watershed_data` mutation path
must be disabled in production or require an explicit recovery-only gate. It
cannot bypass the deployment lease and active-release assertion.

### 14.2 Safety rails for removals

The apply command must refuse unreviewed destructive changes. At minimum:

- every removal must be represented by an exact run ID in the reviewed plan or
  a hashed exact set derived from one identified base collection;
- actual removals must equal the reviewed plan;
- absolute and percentage removal thresholds must be enforced;
- an empty desired inventory is invalid unless an explicit disaster-recovery
  override is supplied;
- source fetch failure cannot be interpreted as an empty dataset; and
- `--runids` must never combine with a global delete behavior.

Globs and prefix matching are prohibited as destructive authorization.

### 14.3 Changed-run reconciliation

Fingerprints allow unchanged runs to remain untouched. For a changed run:

- metadata-only change: update authoritative watershed fields;
- watershed geometry change: update geometry and simplified geometry;
- child change: update retained business identities in place so public API IDs
  remain stable, insert additions, and delete only true removals;
- Parquet change: clear and reapply all fields authoritative to that Parquet
  schema; and
- removal: delete the watershed and cascade only after validation confirms it
  is expected.

This makes repeated deployment efficient without weakening clean-build
reproducibility.

Current subcatchment and channel auto-primary keys are exposed as GeoJSON
feature IDs. Reconciliation must therefore preserve those primary keys for
retained business identities, or a backward-compatible API migration to stable
composite feature IDs must precede the reconciler.

### 14.4 Staging representation

Version 1 uses fixed, logged, attempt-scoped staging tables created by Django
migrations. Deployment performs no activation-time DDL. Proposed tables mirror
the serving watershed, subcatchment, channel, and capability contracts and
include `attempt_id`, source fingerprint, validation state, and canonical
business keys.

The staging implementation must:

- bulk load with `COPY` or equivalent bounded-memory operations;
- enforce uniqueness and type constraints before activation;
- retain enough normalized source data to recompute the reviewed plan inside
  the activation transaction;
- preflight space for artifacts, staging tables, indexes, WAL growth, and the
  verified backup with an explicit margin;
- heartbeat the owning attempt while staging;
- survive a release-tool process crash for diagnosis and safe retry; and
- let `data_release recover` terminalize expired attempts and remove their
  staging rows after the retention window.

Logged staging is the default because it survives database restart and makes
failure recovery explicit. A later unlogged or shadow-schema design requires a
separate durability and cutover review.

## 15. Application and schema deployment coordination

Code, schema, and data releases have different lifecycles but must declare
compatibility.

Recommended order for an additive change:

1. deploy backward-compatible schema migration;
2. deploy application code that can read both old and new data contracts;
3. deploy the new data release; and
4. remove old compatibility code in a later application release.

Breaking changes should follow expand-and-contract migrations. A data release
must declare its contract version, and the apply command must refuse to run
against incompatible code or migrations.

Compatibility is an executable check, not only an audit field. The release and
plan lock:

- an exact schema signature or bounded supported migration range;
- supported data-contract range;
- release-tool image digest and Git commit;
- fingerprint-algorithm version; and
- transformation, GDAL, PostgreSQL, and PostGIS versions that affect output.

Both code and data deploys verify these values before mutation or worker
replacement.

The production entrypoint may retain `migrate` as a safety check, but the
deployment workflow should make migration execution and results explicit
before starting incompatible application workers.

## 16. Rollback and recovery

### 16.1 Failed before activation

No serving rows have changed. Record a failed release attempt, retain diagnostic
reports, release locks, and temporary artifacts according to retention policy,
then release the deployment lock.

An attempt abandoned in `planning` or `staging` remains non-authoritative. Its
heartbeat lease eventually expires, after which `data_release recover` marks it
failed in a separate transaction and cleans its staging rows according to the
diagnostic retention policy.

### 16.2 Failed during activation

The transaction rolls back, leaving the previous data release active. Any
staging objects are retained or marked for cleanup. Because the attempt-status
update inside the domain transaction also rolls back, the exception handler
marks the attempt failed in a separate transaction. The singleton active
release pointer must still reference exactly one previously active release.

### 16.3 Failed after activation

If database invariants pass but application smoke tests fail, run a dedicated
rollback command using the precomputed exact inverse plan. The rollback command
asserts that the failed target is still active, uses retained immutable
artifacts, and applies the same locks and validation rules as a forward deploy.
If persistent state or schema is damaged, enter maintenance mode and restore the
verified backup.

The deployment report must distinguish rollback by reconciliation from restore
from backup. Backup restorability should be tested periodically on a separate
database; archive creation alone is not a restore test. Full restore is a
disaster operation because it also rolls back unrelated authentication,
session, admin, and other writes made after the backup.

### 16.4 Disaster rebuild

Given an empty named volume or new PostgreSQL instance:

1. initialize the database and roles;
2. run all Django migrations;
3. seed explicitly required operational accounts from protected configuration;
4. apply the selected data release;
5. verify database and API invariants; and
6. activate the application.

Silk request history, sessions, and other explicitly nonessential operational
records are not part of the data release.

## 17. Validation contract

Validation occurs at artifact, run, release, and application levels.

### 17.1 Artifact validation

- checksum and byte size;
- expected media type and parseability;
- required fields and data types;
- no unexpected duplicate identity keys;
- CRS and geometry type;
- GeoTIFF and Parquet structural metadata; and
- no credential or HTML error page saved as a data artifact.

### 17.2 Run validation

- exactly one watershed row;
- expected metadata completeness;
- valid, nonempty geometry in EPSG:4326;
- reasonable bounds and area change from the previous release;
- expected subcatchment and channel counts;
- unique child identities;
- no orphan children;
- every Parquet `topazid` has exactly one expected subcatchment, with no
  duplicate Parquet identity; and
- declared RHESSys products pass structural and sample-read checks.

### 17.3 Release validation

- exact desired run ID set;
- exact expected addition and removal set;
- aggregate counts and count deltas within reviewed thresholds;
- all required dataset entries succeeded;
- no unexpired competing attempt exists and every expired attempt in
  `planning`, `staging`, or `applying` has a recoverable terminalization path;
- exactly one `ActiveDataRelease` singleton exists; it may be `EMPTY` only
  before first activation, and every accepted populated release requires
  `ACTIVE` with a non-null pointer;
- manifest and plan hashes match the reviewed release; and
- database fingerprints match the expected clean-build fingerprints for the
  same inputs.

### 17.4 Application smoke tests

- health and database connectivity;
- watershed list and detail endpoints;
- representative geometry, subcatchment, and channel endpoints;
- SBS endpoint for a run that declares SBS data;
- RHESSys catalog and one representative tile or query for each capability
  mode; and
- known removed run returns not found.

## 18. Observability and audit

Every attempt should emit structured logs and a machine-readable report with:

- release, manifest, plan, code, and workflow identities;
- operator and target environment;
- previous and resulting active release;
- artifact fetch/cache results without credentials;
- per-run action and input fingerprints;
- expected and actual counts;
- duration by phase;
- validation results;
- backup artifact identity;
- activation or rollback outcome; and
- cache cleanup recommendations.

The active release ID should be exposed through an authenticated status command
and optionally an application health/status endpoint.

## 19. Storage and retention

### 19.1 PostgreSQL

- pin the currently running Postgres/PostGIS image by digest before changing
  storage, without combining the storage cutover with a database upgrade;
- migrate the live anonymous volume to a named `postgres_data` volume using the
  one-time cutover runbook below;
- never use `docker compose down -v` in ordinary deployment;
- monitor free space and table growth; and
- set a retention policy for Silk, especially response bodies, so operational
  tracing does not dominate database size.

Adding the Compose mount directly would create an empty database. The one-time
cutover must therefore:

1. identify one canonical production checkout and Compose project and correct
   systemd to use `compose.prod.yml` explicitly;
2. create and verify an encrypted off-host logical backup;
3. enter maintenance mode and quiesce database writes;
4. provision the named volume with the pinned current image;
5. restore the logical backup, or use a separately reviewed physical-copy
   procedure compatible with the exact database version;
6. verify roles, extensions, migrations, release state, table counts,
   fingerprints, and application smoke tests;
7. switch Compose and systemd to the named volume; and
8. retain the stopped anonymous volume until the cutover is accepted and the
   rollback window closes.

### 19.2 Data artifacts

DB10 follows the operator's decision to use the existing ZFS-backed
`forest1:/wc1` filesystem. DB10A provisions and accepts the test and production
directories defined by the
[artifact backup contract](database-artifact-store-contract.md).

- use the operator-owned `/wc1/utility-watershed-analytics-artifacts/v1` tree;
- keep it separate from `/wc1/utility-watershed-analytics-db-backups`;
- use private filesystem modes, content-addressed keys, and verified copies;
- keep artifacts for the active release and at least two rollback releases;
- use content-addressed keys so identical artifacts are shared safely;
- garbage-collect only blobs unreferenced by retained manifests;
- record licensing or sensitivity constraints where relevant; and
- ensure TTL policies cannot remove accepted release artifacts.

### 19.3 Local cache

Version 1 cache paths, hit verification, atomic promotion, concurrency, cleanup,
and storage-unavailable behavior are defined by the
[artifact-store contract](database-artifact-store-contract.md).

- verify content on every cache hit;
- download to a temporary file and atomically rename after verification;
- do not modify a content-addressed cache entry;
- allow safe concurrent readers; and
- clean unreferenced entries only outside an active build.

### 19.4 Backups

The repository-owned operational commands, scheduler units, credential
contract, retention procedure, maintenance sequence, disaster restore, and
selective restore process are defined in the
[database backup and restore runbook](runbooks/database-backup-restore.md).
That runbook does not authorize production execution.

- every destructive deployment and storage cutover requires a newly verified,
  encrypted off-host backup before activation;
- retain backups for the active release and at least two rollback releases;
- run scheduled encrypted off-host backups now with a default maximum
  recovery-point objective of 24 hours until a stricter product requirement is
  defined;
- test restore into an isolated database on a schedule and before relying on a
  new backup or database-image format; and
- document maintenance-mode entry, restore, verification, and exit procedures.

## 20. Security

- keep JWTs and database credentials in protected deployment secrets;
- avoid credentials in URLs, process listings, plans, and logs;
- remove the production PostgreSQL host port unless it is required, or bind it
  only to `127.0.0.1` while application containers use the Compose network;
- create any temporary environment file with mode `0600`, minimize its
  contents, and guarantee cleanup on success, failure, and cancellation;
- use least-privilege database roles for planning, staging, and applying where
  practical;
- restrict production data deployment through an approved environment;
- treat backups and database-global dumps as sensitive;
- verify artifact transport and content hashes; and
- record who approved and applied each release.

## 21. Proposed implementation phases

### Phase 0: production safety

- pin the currently running PostGIS image without upgrading it;
- execute the backed-up, quiesced, verified cutover from the anonymous volume
  to a named PostgreSQL volume;
- select one canonical checkout and Compose project and correct systemd to use
  `compose.prod.yml`;
- serialize current code deployments with a shared host lock;
- remove or loopback-bind the PostgreSQL host port and protect temporary
  environment files with mode `0600`;
- correct deployment documentation and systemd Compose-file usage;
- establish Silk retention or disable unnecessary response capture;
- establish scheduled encrypted off-host backups with a 24-hour default RPO,
  retention, and periodic restore tests;
- prohibit `load_watershed_data --force` in production, especially the
  globally destructive `--force --runids` combination.

### Phase 1: release representation

- maintain the accepted version-1 release, member-index, artifact,
  transformation, RHESSys, validation, and compatibility schemas;
- create the first manifest from the authoritative inventory;
- require distinct immutable collection and watershed keys;
- define field-by-field metadata authority and exact child business keys;
- implement content-addressed artifact storage and cache layout; and
- generate separately keyed forward, rollback, and empty-build plans.

### Phase 2: strict clean builder

- make required source failures fatal;
- implement deterministic preparation and NASA enrichment;
- build into an empty CI database;
- add integrity constraints and validation commands; and
- prove that two independent empty builds produce identical watershed-domain
  fingerprints.

### Phase 3: transactional reconciler

- add the release, active-pointer, attempt-lease, and per-run state models;
- implement logged attempt-scoped staging and recovery;
- implement metadata and child upserts that preserve retained public IDs,
  capability serving rows, and exact expected deletion;
- add transaction locking, expected-base assertions, and removal safety rails;
- prove that applying an active release again makes zero domain changes; and
- preserve non-watershed Django state.

### Phase 4: deployment integration

- implement `scripts/deploy_database.sh`;
- build a one-off release-tool image from the repository root and pin it by
  digest;
- add protected code/data workflows with one shared production concurrency
  group and explicit one-shot migrations;
- integrate verified off-host backup, base-specific plan approval, smoke tests,
  reports, and exact inverse rollback;
- expose active release status; and
- update the inventory snapshot automatically or from the deployment report.

### Phase 5: optional blue-green data deployment

- measure staging and activation time;
- evaluate a second database or versioned-schema cutover if in-place activation
  becomes too slow;
- separate persistent application state if full-database replacement is
  adopted; and
- retain the same release manifest and validation contracts.

## 22. Acceptance criteria for the first production-capable version

The tooling is ready to replace the current manual loader workflow when it can
demonstrate all of the following:

1. Build the accepted inventory from an empty database.
2. Apply the same release twice with a zero-change second plan.
3. Remove one reviewed watershed without affecting unrelated runs.
4. Apply a metadata-only change without rebuilding unchanged child rows.
5. Add a batch and validate its exact locked membership.
6. Replace the NASA batch using a deterministic, audited enrichment artifact.
7. Replace Mill Creek and validate its re-vendored RHESSys capability.
8. Abort a release with one missing required source while leaving production
   unchanged.
9. Reject an unexpected large removal or empty upstream result.
10. Roll back to the previous compatible data release.
11. Reconstruct the active watershed data after loss of the PostgreSQL volume.
12. Produce a report sufficient to identify every input and code revision used.
13. Preserve retained watershed, subcatchment, and channel public identities.
14. Reject a plan whose active base, schema signature, or materializer digest
    differs from the reviewed values.
15. Prevent code/schema deployment and data activation from running
    concurrently.

## 23. Recommended defaults and remaining decisions

The architecture adopts these defaults unless an implementation proposal
documents and approves a replacement:

1. Accepted artifact backups use the operator-owned `forest1:/wc1` filesystem,
   private modes, content-addressed keys, verified atomic copies, and no TTL
   while referenced by a retained release.
2. Every non-watershed Django table is persistent by default. Only explicitly
   declared watershed-domain and capability tables are reconciled; Silk has a
   separate expiry policy.
3. Every watershed receives a mandatory immutable `watershed_key` now. `runid`
   remains a replaceable source revision and compatibility alias.
4. The reviewed hashed member index is authoritative. Intentional exclusions
   require pull-request review, and destructive authorization always resolves
   to exact run IDs.
5. Metadata authority is defined field by field. Successor run IDs and
   geometries are target-authoritative; unresolved conflicts fail preparation.
6. Accepted RHESSys assets move to the durable project-controlled namespace and
   are served through atomically materialized capability configuration.
7. Merging a release pull request does not deploy it. Production application
   requires a protected manual action and a reviewer distinct from the release
   preparer.
8. Retain at least the active release plus two rollback releases, including
   their artifacts, plans, reports, and verified off-host backups.
9. The complete release-tool image, pinned by digest, is the reproducibility
   contract for Python, GDAL, transformation libraries, and client tools.

The remaining project-specific decisions are:

1. What naming scheme assigns watershed keys to existing batch members, and
   when do public routes migrate from run IDs with compatibility redirects?
2. What is the complete field-level metadata precedence matrix for each
   collection?
3. What activation lock-time and API-latency budget triggers blue-green
   deployment?
4. Does persistent application state require an RPO shorter than the proposed
   24-hour default?
5. Which people or teams may prepare, independently approve, deploy, and roll
   back a release?

Until these are resolved, release preparation and planning can be implemented
without authorizing automatic production mutation.
