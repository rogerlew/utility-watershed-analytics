# Database artifact-store contract

Status: accepted version 1 contract

Date: 2026-07-17

This document selects and governs durable storage for release artifacts. It is
a design and acceptance contract only. DB10 does not create an account, bucket,
key, cache, mirror, or real artifact; DB10A must observe the provisioned test
and production infrastructure before any later package relies on it.

## 1. Provider decision

Version 1 selects **Backblaze B2 Cloud Storage** in an assigned United States
region through its HTTPS S3-compatible API.

Backblaze is the simplest provider that meets this project's actual needs:

- its [S3-compatible API](https://www.backblaze.com/docs/cloud-storage-call-the-s3-compatible-api)
  supports the multipart, object-version, encryption, and Object Lock calls the
  future client needs;
- [Object Lock](https://www.backblaze.com/docs/cloud-storage-object-lock)
  supports retention and legal holds through S3 and native APIs, and locked
  objects resist lifecycle deletion;
- [application-key capabilities](https://www.backblaze.com/docs/cloud-storage-s3-compatible-app-keys)
  separate object read/write/delete, bucket retention, object retention/legal
  hold, and governance-bypass authority and can be bucket/prefix scoped;
- default [SSE-B2 encryption](https://www.backblaze.com/docs/cloud-storage-server-side-encryption)
  provides AES-256 at rest without a separate customer key that this single
  operator could lose;
- [event notifications](https://www.backblaze.com/docs/cloud-storage-event-notifications),
  [access-log capabilities](https://www.backblaze.com/docs/cloud-storage-application-key-capabilities),
  and [caps/alerts](https://www.backblaze.com/docs/cloud-storage-data-caps-and-alerts)
  provide the controls DB10A must accept; and
- current [B2 pricing](https://www.backblaze.com/cloud-storage/pricing) has no
  minimum storage duration and is appropriate for a small public-data archive.

Cloudflare R2 remains a reasonable transfer-cost option, but its official
[S3 compatibility matrix](https://developers.cloudflare.com/r2/api/s3/api/)
does not implement S3 Object Lock configuration. Its separate
[bucket-lock rules](https://developers.cloudflare.com/r2/buckets/bucket-locks/)
can protect prefixes but require Cloudflare-specific administration. AWS S3 has
the strongest native control surface—its
[Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html),
[encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/specifying-s3-encryption.html),
and [access logging](https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-server-access-logging.html)
meet the contract—but IAM, logging, and account administration add complexity
that is not justified for public, non-PII artifacts and one operator.

Known B2 constraints are accepted:

- bucket names are globally unique and the assigned S3 region/endpoint is
  recorded only when DB10A provisions the account;
- Object Lock must be deliberately enabled and default retention configured;
- a COMPLIANCE retention mistake cannot be shortened, so version 1 uses a
  reviewed 365-day default rather than indefinite provider retention; and
- provider durability is not provider independence, so an independently
  verified `forest1` mirror is mandatory for the active plus two rollback
  releases.

## 2. Ownership and namespaces

One project-controlled Backblaze account owns both buckets. The account uses a
project recovery email, MFA, and offline recovery material. Master/account
credentials are never placed on `forest1`, `wepp3`, application containers,
deployment runners, or command lines.

DB10A creates exactly two private buckets using globally unique names matching:

- `uwa-artifacts-test-<account-suffix>`; and
- `uwa-artifacts-prod-<account-suffix>`.

Test credentials cannot access production and production credentials cannot
access test. Bucket and object metadata must not contain secrets, personal
names, PII, or unreleased source URLs.

## 3. Encryption and immutability

Both buckets require before the first accepted object:

- HTTPS-only S3 access;
- default SSE-B2 AES-256 encryption;
- Object Lock enabled with default 365-day COMPLIANCE retention;
- private access with no unauthenticated object listing or download; and
- lifecycle rules that cannot remove retained or locked objects.

SSE-C is prohibited in version 1. These artifacts are public and contain no
PII, while losing a separate customer-managed encryption key would make the
only durable rebuild source unreadable. Provider-managed encryption plus strict
role separation is the simpler recovery-safe choice.

## 4. Content-addressed layout

Every durable object uses one key:

```text
v1/blobs/sha256/<first-two-hex>/<full-lowercase-sha256>
```

Manifests, member indexes, plans, lineage, validation reports, geospatial data,
Parquet, and GeoTIFF objects all use the same layout. Media type, byte count,
license/provenance class, and SHA-256 remain in the reviewed release metadata.
Mutable aliases such as `latest` may be created later for humans, but no
manifest, plan, cache, deployment, or recovery procedure may treat them as
authority.

Publication streams to multipart upload, completes only after every part
succeeds, verifies source SHA-256 before upload, then reads back and verifies
SHA-256, size, and media type. An existing key is success only after full
verification. Different bytes at the claimed key are a collision/integrity
incident: stop, preserve both inputs outside the authoritative prefix, and
never overwrite. Failed multipart uploads are aborted immediately; exact
orphans older than 24 hours are reviewed and aborted.

## 5. Access roles and credentials

| Role | Stored where | Allowed | Explicitly denied |
| --- | --- | --- | --- |
| Publisher | Protected preparation environment | Bucket/prefix-scoped list, read, multipart write. | Delete, lock/retention changes, bucket/key/log administration, other environment. |
| Runtime reader | Protected application runtime | Exact object read/head only. | List, write, delete, retention, bucket administration. |
| Deployment reader | Protected deployment environment | List/read plus retention inspection. | Write, delete, retention mutation, bucket/key administration. |
| Retention administrator | Offline operator context | Exact list/read/delete and object retention/legal-hold changes. | Governance bypass, bucket/key/log administration, deployed use. |
| Account owner/break-glass | Offline account recovery | Buckets, encryption, keys, lock defaults, logs, events, caps, alerts, disaster recovery. | Routine publication, deployment, runtime use. |

Credentials use protected environment injection only:

```text
UWA_ARTIFACT_ENDPOINT
UWA_ARTIFACT_BUCKET
UWA_ARTIFACT_REGION
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

Values never appear in Git, manifests, plans, artifact URIs, logs, process
arguments, or evidence. Each role and environment rotates independently. A
revoked key is a hard preflight failure, not a warning or reason to reuse a
broader key.

## 6. Retention and garbage collection

The retained set is graph reachability from exactly:

1. the active release;
2. rollback release 1; and
3. rollback release 2.

All blobs reachable from those three releases have no TTL. Provider retention
may expire after 365 days, but expiration never makes a retained blob eligible
for deletion. Release promotion first verifies provider objects and the
independent mirror for the new active-plus-two set.

Garbage collection is manual and quarterly in version 1. The retention
administrator produces a deterministic preview of exact unreferenced keys.
Deletion is allowed only when a blob is unreachable from every retained
manifest, no build/cache lease references it, its provider lock has expired,
the independent mirror policy permits deletion, and the preview is approved.
No prefix, age-only rule, wildcard, or storage-pressure event authorizes GC.

## 7. Local cache and provider outage

The implementation target is
`/var/cache/utility-watershed-analytics/artifacts/v1/sha256/<prefix>/<hash>`.
The cache verifies SHA-256 on every hit, downloads into a unique temporary file,
and atomically promotes only verified bytes. Content entries are never edited
in place. Concurrent readers are safe; cleanup runs only outside active builds
and never makes the cache authoritative.

A provider timeout, 5xx response, missing object, revoked credential, or digest
mismatch fails preparation/deployment before activation. Existing active state
does not change. Already verified local objects may continue serving where the
application supports them, but the system does not claim a missing capability
is available.

## 8. Independent recovery and responsibilities

`forest1` will hold a verified independent mirror at
`/wc1/utility-watershed-analytics-artifact-recovery/v1` for the active plus two
rollback releases. This path is a DB10A provisioning target, not a DB10-created
directory. The mirror is refreshed and hash/inventory checked after publication
and before activation. A quarterly isolated drill restores all three releases
into a clean test namespace and compares every manifest and blob hash.

- Publisher owns verified upload and multipart cleanup.
- Deployment reader owns verified fetch/cache quarantine and preflight.
- Retention administrator owns reachability preview, lock-aware GC, and retained
  inventory comparison.
- Account owner owns MFA/recovery, bucket policy, role/key rotation, logging,
  alerts/caps, provider incident response, and mirror-to-provider restoration.
- Release approver owns the exact active/rollback set and license/provenance
  acceptance; storage operators do not infer release retention.

## 9. Artifact governance matrix

The authoritative machine-readable matrix is
`data-releases/storage-contract/v1/artifact-classes.json`.

| Class | Examples | License/provenance | Sensitivity and residency | Retention |
| --- | --- | --- | --- | --- |
| Release control | Manifest, index, plan, compatibility, lineage | Repository license plus exact upstream provenance. | Public, no PII, US. | Active plus two, no TTL. |
| Watershed vector | Boundary, subcatchments, channels, hillslopes | Upstream license and attribution required. | Public, no PII, US. | Active plus two, no TTL. |
| Thematic/tabular | Metadata, utility enrichment, soils, land use | Upstream license and transformation provenance required. | Public, no PII, US. | Active plus two, no TTL. |
| RHESSys input | Spatial inputs and Parquet | Input license, attribution, and model version required. | Public, no PII, US. | Active plus two, no TTL. |
| RHESSys output | Scenario GeoTIFF and derived Parquet | Derived-output license, input provenance, and model version required. | Public, no PII, US. | Active plus two, no TTL. |
| Validation evidence | Reports and sanitized summaries | Repository license; summaries sanitized. | Public-sanitized, no PII, US. | Active plus two and at least one year. |

An artifact with unknown or incompatible licensing, personal data, required
non-US residency, or an unsanitized report fails preparation. The contract may
be extended through review; the publisher cannot waive it.

## 10. Failure review and DB10A handoff

`data-releases/storage-contract/v1/threat-review.json` assigns prevention,
detection, response, owner, and a DB10A proof for partial upload, hash collision,
stale cache, revoked credentials, provider outage, accidental deletion,
active-plus-two restoration, compromised publisher, and lifecycle
misconfiguration.

DB10A must provision and observe both buckets, default encryption and lock,
access logs/events/caps/alerts, all environment-separated roles, rotation and
denial behavior, interrupted upload cleanup, lock-protected deletion denial,
independent mirror creation, and a clean restore of all three retained test
releases. Until that package is `EXECUTED-COMPLETE`, no later package may treat
the provider endpoint, bucket names, credentials, logs, alerts, or recovery
mirror as accepted infrastructure.
