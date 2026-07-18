# DB10 validation evidence

Date: 2026-07-17

Environment: `forest1`, repository `/workdir/utility-watershed-analytics`,
branch `agent/database-backup-deployment-spec`, starting revision
`040f045bf0f24ef58df70c4996d8e728591125ed`

Evidence mode: Mixed. Provider capabilities are Static evidence from official
documentation current on the review date. Repository checks are Ran evidence.
No provider account, bucket, credential, object, cache, mirror, database, or
production system was created or accessed.

## Provider selection evidence

Backblaze B2 was selected over Cloudflare R2 and AWS S3 for the version-1
public-data artifact store:

- B2's official S3 documentation lists multipart, encryption, object versions,
  and Object Lock operations.
- B2 Object Lock supports S3/native retention and legal hold, and locked files
  resist lifecycle deletion.
- B2 application-key capabilities separately expose read/write/delete, bucket
  and object retention, legal hold, governance bypass, logging, and notification
  administration with bucket/prefix restrictions.
- SSE-B2 supplies provider-managed AES-256 at rest. Event notifications, bucket
  access logs, data caps, and anomaly alerts exist for DB10A acceptance.
- R2's S3 matrix does not implement S3 Object Lock configuration; its separate
  bucket-lock API would add provider-specific client/administration behavior.
- AWS S3 meets every control but adds IAM/logging/account complexity not needed
  for one operator and public no-PII data.

Source links and accepted limitations are preserved in
`docs/database-artifact-store-contract.md`. This review selects the provider;
only DB10A can prove the provisioned behavior.

## Contract coverage

The 11,835-byte machine-readable corpus validates:

- two private, environment-separated buckets;
- project account ownership, MFA, offline recovery, SSE-B2 AES-256, TLS, and
  365-day COMPLIANCE Object Lock;
- publisher, runtime reader, deployment reader, retention administrator, and
  account-owner/break-glass roles;
- exact SHA-256 key layout and immutable collision handling;
- multipart verification/cleanup, active-plus-two no-TTL reachability, reviewed
  lock-aware GC, verified local cache, and independent `forest1` mirror;
- six artifact classes with license, sensitivity, PII, residency, and retention
  declarations; and
- nine cases covering all roadmap failures plus compromised publisher and
  lifecycle misconfiguration.

## Executed gates

```text
PYTHONDONTWRITEBYTECODE=1 python scripts/validate_artifact_store_contract.py
{"artifact_classes": 6, "buckets": 2, "roles": 5, "status": "passed", "threat_cases": 9}

PYTHONDONTWRITEBYTECODE=1 python -m unittest scripts.tests.test_artifact_store_contract
..........
Ran 10 tests
OK
```

The ten tests reject provider drift, publisher delete authority, short lock
duration, fewer than three releases, missing artifact/failure coverage, mutable
key authority, incomplete mirror, and a public production bucket.

The full data-contract CI shape also passed:

- DB08: seven schemas, seven valid cases, nine negative cases, seven tests;
- DB09: five fingerprint subjects, four plan schemas, three plans, five semantic
  mutations, twelve tests;
- all repository JSON syntax;
- Ruff across DB08–DB10 contract Python;
- Python tab checks and Ruby workflow-YAML parsing; and
- `git diff --check`.

Relative Markdown links/code fences, exact changed paths, and focused GitHub,
AWS-key, and private-key pattern review passed during closeout. Actionlint and
host Ruff were unavailable; isolated Ruff passed. Server/client/database suites
were not applicable.

## DB10A acceptance boundary

DB10A must observe exact endpoint/region/bucket identities, encryption and lock
defaults, role denials, rotation, logs/events/caps/alerts, partial cleanup,
locked deletion denial, mirror inventory, provider outage behavior, and clean
active-plus-two restoration. Until then, every infrastructure claim remains
unproven and no later client may depend on provider credentials or bucket state.
