# DB10 — Durable artifact-store contract

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB10`

Evidence mode: Mixed

Execution authorization: The user authorized scaffold and execution on
2026-07-17. Authority is limited to repository changes, current official
provider-documentation review, and local validation on `forest1`; account,
bucket, credential, production, commit, push, and pull-request actions are not
authorized.

## Objective

Select a simple project-controlled S3-compatible artifact provider and freeze
the ownership, immutability, encryption, role, key-layout, retention, garbage
collection, cache, recovery, licensing, sensitivity, and residency contract
required before DB10A provisions infrastructure.

## Scope

Included:

- provider comparison and selection;
- separate private test and production bucket requirements;
- Backblaze-managed AES-256 default encryption and TLS transport;
- Object Lock COMPLIANCE retention and active-plus-two logical retention;
- publisher, runtime reader, deployment reader, retention administrator, and
  account-owner/break-glass boundaries;
- SHA-256 content-addressed keys and collision handling;
- multipart publication, verification, cache, garbage-collection, outage, and
  restore behavior;
- machine-readable artifact-class governance and threat/failure review;
- standard-library validation/tests and data-contract CI integration; and
- explicit DB10A acceptance handoff.

Excluded:

- creating a Backblaze account, buckets, keys, lock rules, logs, alerts, caps,
  recovery mirror, DNS, or protected environment configuration;
- real uploads/downloads, source artifacts, production access, deployment, or
  destructive storage action;
- DB11 release CLI/image and DB12 artifact client/cache implementation; and
- DB backup storage changes: DB01's restic repository remains separate.

## Frozen decisions

- Provider: Backblaze B2 Cloud Storage, using its HTTPS S3-compatible API in an
  assigned US region. The choice is based on S3 compatibility, COMPLIANCE
  Object Lock, prefix/bucket-scoped application-key capabilities, SSE-B2,
  access logging/events/caps, and lower single-operator complexity.
- Ownership: one project-controlled account with MFA and offline recovery
  material; separate private globally unique test and production buckets.
- Encryption: default SSE-B2 AES-256 at rest; TLS in transit. SSE-C is rejected
  because losing a separately managed key would make public rebuild artifacts
  unrecoverable without adding useful confidentiality for this no-PII service.
- Immutability: Object Lock enabled before first accepted object, default
  COMPLIANCE retention of 365 days. Lifecycle rules may not delete retained or
  locked objects.
- Retention: all objects reachable from the active release and two exact
  rollback releases are retained without TTL. Other unreferenced blobs become
  GC candidates only after lock expiry and a reviewed quarterly preview.
- Keys: `v1/blobs/sha256/<first-two-hex>/<full-lowercase-sha256>` only. Every
  release object, including manifests/plans/reports, is a blob. No mutable
  `latest` or semantic alias is deployment authority.
- Roles: publisher has read/write but no delete or retention administration;
  runtime reader has object read only; deployment reader has list/read and
  retention-read; retention administrator is offline and owns exact GC plus
  object-retention changes without governance bypass; account owner alone owns
  buckets, encryption, keys, locks, logs, alerts, and break-glass recovery.
- Recovery: production activation requires verified provider bytes plus a
  verified independent `forest1` recovery mirror for active plus two rollback
  releases. Provider outage fails closed and never changes active state.

## Authority and sources

- Governing roadmap: `docs/ROADMAP.md`, DB10 and DB10A.
- Architecture: `docs/database-deployment-architecture.md`, sections 19 and 20.
- Release/fingerprint inputs: `docs/database-release-schema-contract.md` and
  `docs/database-fingerprint-plan-contract.md`.
- Official provider sources reviewed 2026-07-17: Backblaze B2 S3 API, Object
  Lock, application-key capabilities, server-side encryption, event
  notifications, access logging/security, caps/alerts, regions, and pricing;
  Cloudflare R2 S3 compatibility/bucket locks; AWS S3 Object Lock/encryption.
- Starting revision: `040f045bf0f24ef58df70c4996d8e728591125ed`.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository, official public documentation, and local
  `forest1` validation only
- Mutation boundary: DB10 contract, fixtures, validator/tests, CI, architecture,
  roadmap, catalog, and package evidence

## Gates

- exact provider rationale and known limitations recorded from official docs;
- machine-readable policy covers both buckets, five roles, encryption, lock,
  key layout, three-release minimum, GC/cache/recovery responsibilities;
- every artifact class has license, sensitivity, residency, and retention;
- threat review covers partial upload, hash collision, stale cache, revoked
  credentials, provider outage, accidental deletion, and active-plus-two restore;
- tests mutate role privilege, lock duration, retained count, class coverage,
  failure coverage, key layout, and recovery mirror requirements;
- existing DB08/DB09 contract gates remain green;
- JSON/Python/Ruff/YAML/Markdown/secret/diff checks pass; and
- no account, bucket, credential, real artifact, production access, or bulky
  data is created.

Skipped gates:

- live S3/API and cross-role denial tests: DB10A owns provisioned acceptance;
- client/cache integration: DB12;
- server/client/database suites: no application or database behavior changes.

## Exit criteria

`EXECUTED-COMPLETE` requires provider selection, complete policy and threat
fixtures, mutation tests, CI integration, authoritative documentation, and an
explicit DB10A acceptance checklist. A live infrastructure claim is prohibited.

Hold outcomes:

- `EXECUTED-HOLD-PROVIDER`: no candidate satisfies required controls simply;
- `EXECUTED-HOLD-POLICY`: an artifact class or failure lacks an owner/control;
- `EXECUTED-HOLD-RECOVERY`: active plus two rollback releases cannot be restored
  independently of the provider.

## Artifacts

- `artifacts/db10-validation-evidence.md`

## Execution record

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Provider and DB08/DB09 handoff review | official docs / repository | Mixed | Backblaze B2 selected; repository-only boundary, policy vocabulary, DB10A separation, gates, and holds frozen. |
| Provider capability/limitation comparison | official Backblaze, Cloudflare, and AWS docs | Static | B2 S3 API, Object Lock, key capabilities, SSE-B2, logs/events/caps, regions, and pricing reviewed; R2 S3 lock gap and AWS complexity recorded. |
| `python scripts/validate_artifact_store_contract.py` | `forest1` | Ran | Two buckets, five roles, six artifact classes, and nine threat cases passed. |
| `python -m unittest scripts.tests.test_artifact_store_contract` | `forest1` | Ran | Ten fail-closed policy mutation tests passed. |
| Existing DB08/DB09 contract gates | temporary Python 3.12 environment / `forest1` | Ran | Seven DB08 tests and twelve DB09 tests plus their validators remained green. |
| JSON, Python, Ruff, YAML, link, fence, secret-pattern, and diff review | repository / `forest1` | Mixed | Applicable checks passed; no infrastructure or application code changed. |

## Findings

- Backblaze B2 supplies the required controls with less single-operator
  complexity than AWS and more S3-native lock/role coverage than R2.
- COMPLIANCE retention mistakes cannot be shortened. The reviewed 365-day
  default plus no-TTL active/rollback reachability is intentionally conservative
  and DB10A must prove it before first accepted object.
- Provider durability is not independent recovery; the exact `forest1` active
  plus two mirror and quarterly clean restore are mandatory acceptance gates.
- All current artifact classes are public/public-sanitized, prohibit PII, and
  require US residency plus explicit license/provenance.

## Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: provider, governance/failure fixtures, tests, CI,
  authoritative contract, and DB10A handoff passed without provisioning
- Successor: DB10A infrastructure acceptance

## Closeout checklist

- [x] Status and evidence are accurate.
- [x] Provider sources and limitations are recorded.
- [x] Artifact and failure coverage is complete.
- [x] No infrastructure or credentials were created.
- [x] Authoritative docs, catalog, and roadmap are reconciled.
- [x] Commit, push, and PR actions match authorization.
