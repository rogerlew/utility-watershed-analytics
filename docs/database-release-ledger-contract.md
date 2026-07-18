# Database Release Ledger and Capability Contract

Status: DB15 accepted

Date: 2026-07-17

This document defines the version-1 release ledger implemented by migration
`watershed.0009_release_ledger_capabilities`. It records accepted release
coordinates and capability-serving intent. It does not stage, reconcile, fetch,
back up, or activate real data.

## Ledger records

| Model | Durable role |
| --- | --- |
| `DataRelease` | Immutable manifest, semantic fingerprints, version contracts, materializer identity, predecessor, expected/actual aggregate counts, validation summary, and retained lifecycle status. |
| `ActiveDataRelease` | One lockable singleton representing either `EMPTY` or one coherent active release. |
| `DataReleaseAttempt` | Attributable operator/workflow execution, reviewed and actual plan hashes, timestamps, one bounded lease, backup/report references, and sanitized terminal failure. |
| `DataRunState` | One release-scoped row per logical watershed and source run, with accepted fingerprints, counts, and validation state. |
| `DataArtifactLineage` | Immutable content identity, durable HTTPS location, byte size, media type, and role for one release run. |
| `RunCapability` | Release-scoped RHESSys mode, durable base/index locations, immutable index checksum, fingerprint, and public runtime configuration. |

All schema, data, identity, artifact, and fingerprint contract versions are
exactly version 1. Release IDs use `YYYY-MM-DD.N`. Digests and materializer
coordinates use the DB08/DB09 lowercase SHA-256 and Git formats. Unknown
versions or malformed coordinates fail database/model validation.

Release payload and artifact lineage fields cannot be changed with normal model
saves after insertion. Release lifecycle and the active pointer can change only
through the bounded activation helper. Database constraints additionally allow
only one `active` release status and one singleton row.

## Singleton and activation

The migration creates exactly one `ActiveDataRelease(singleton_id=1)` in
`EMPTY`. The database check requires every `EMPTY` coordinate to be null and
every `ACTIVE` coordinate to be present.

`activate_release(attempt)` runs in one transaction. It:

1. locks the singleton, attempt, and target release;
2. requires an `applying` attempt and exact reviewed/actual plan match;
3. reasserts the expected previous active release;
4. verifies aggregate run counts, run validation, logical collection identity,
   and declared capability row/fingerprint agreement;
5. supersedes the old release, activates the target, updates the singleton, and
   completes the attempt; and
6. commits all state changes together or none of them.

A previously superseded release may be activated again by a newly reviewed
attempt whose expected base is the current release. This preserves both release
histories and supplies the DB15 rollback schema without implementing the later
rollback command.

## Attempts and leases

An attempt is attributed to either `operator` or `workflow` plus a bounded
identifier; DB15 introduces no application user or PII record. Legal states are
`planning`, `staging`, `applying`, `succeeded`, `failed`, and `rolled_back`.
The transition helper rejects skipped or terminal-to-active transitions and
sets the corresponding timestamps.

At most one attempt has `lease_active=true`. Owner, heartbeat, and expiry are
stored on that attempt. An expired lease remains a conflict and reports that
recovery is required; it never grants silent takeover. DB16 owns recovery and
staging cleanup.

Failure summaries are single-line and limited to 512 characters. Common
password, token, secret, API-key assignments and URI user information are
replaced with `[REDACTED]` before model persistence. Full logs and credentials
do not belong in the ledger.

## Capability visibility

Capability rows are release history. Staging a successor row does not make it
serving state. Application code must query:

```python
RunCapability.objects.visible()
```

That query joins through the singleton active pointer. The activation
transaction therefore changes release status, pointer, and capability
visibility atomically. Version 1 supports the accepted `rhessys` capability
with `dynamic`, `precomputed`, or `both` mode. Runtime configuration must be
public and rejects secret-bearing keys.

Durable serving and index references remain HTTPS values from the DB08
capability contract. The operator-owned
`forest1:/wc1/utility-watershed-analytics-artifacts/v1` tree remains the
separate content-addressed backup/cache selected by DB10–DB12; DB15 does not
replace or externalize it.

## Ownership and compatibility

Release, attempt, run, artifact, and capability rows are retained ledger
history and use protected foreign keys. They are outside DB14's three-table
serving rebuild. A future reconciler writes a target release's capability rows
before activation but must not delete older release history.

DB15 is additive and old application code ignores its tables. Production
migration and release activation require later packages with separate backup,
maintenance, plan, staging, reconciliation, and production authority.
