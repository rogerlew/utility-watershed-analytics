# DB15 validation evidence

Date: 2026-07-17

Host: `forest1`

Starting revision: `06cb3153f47ede052a8dc3ca06716bbd817a5592`

No production host, database, source API, real release artifact, credential,
or user record was accessed. All database evidence used disposable PostGIS on
isolated Docker networks with synthetic identifiers and geometry.

## Focused lifecycle proof

The final focused ledger and migration suite passed 11 tests. It covers:

- migration bootstrap of exactly one coherent `EMPTY` singleton and clean
  reverse migration;
- database rejection of a second singleton and incompatible contract version;
- immutable release coordinates and artifact lineage;
- release/run/artifact/capability uniqueness;
- public capability configuration and logical-identity agreement;
- operator and workflow attribution;
- one active lease, observable expiry, and no silent expired-lease takeover;
- legal and illegal attempt transitions;
- redaction and line/length bounding of failure summaries;
- first and successor activation with retained history;
- reactivation of a superseded release for rollback;
- exact plan and capability mismatch rejection; and
- capability invisibility before activation and exact active-release visibility
  after the singleton transaction.

## Production-shaped migration rehearsal

Synthetic existing serving data matched the accepted DB06 aggregate. Migration
`0009` created only ledger/capability tables and the singleton. Forward and
reverse migration preserved all serving counts and sampled child IDs.

```json
{
  "checks": {
    "empty_singleton_bootstrapped": true,
    "forward_reverse_preserved_domain": true,
    "seed_counts_match": true
  },
  "counts": {
    "channels": 86895,
    "subcatchments": 195457,
    "watersheds": 126
  },
  "forward_seconds": 0.242,
  "rollback_seconds": 0.284,
  "status": "passed"
}
```

The timings are isolated forest1 evidence, not a production guarantee or
production migration authority.

## Full gates

The final production server image was:

```text
sha256:f4cdbd004811c30961d8fee2e9393e0b10a44c468a1befc3a49fc2a6f196b966
```

Ruff passed. `makemigrations --check --dry-run` reported `No changes detected`
plus the expected non-fatal warning because that command intentionally had no
database container. All 149 server tests passed against fresh disposable
PostGIS.

Python syntax, documentation links and fences, literal-secret assignment scan,
new/diff-line whitespace, `git diff --check`, and disposable-container cleanup
passed. No DB15 container remained running.
