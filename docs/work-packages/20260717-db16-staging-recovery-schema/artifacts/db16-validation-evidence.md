# DB16 validation evidence

Date: 2026-07-17

Host: `forest1`

Starting revision: `17c0626dc7d8d8ca8cbd737861086bb75a7f5202`

Evidence mode: Mixed

No production host, production database, release artifact, credential, source
data, or `/wc1` production path was accessed.

## Schema and focused tests

The migration creates one staging-state table and four fixed attempt-scoped
target tables. PostgreSQL catalog inspection confirmed all five are logged
tables. Forward and reverse migration preserved the existing watershed domain,
including the `EMPTY` singleton.

```text
focused staging and migration tests: 11 passed in 13.557s
makemigrations --check --dry-run: no changes detected
```

The focused suite covers exact-fit and one-byte-short capacity decisions, every
named capacity component, bounded 2,501-row loading, per-chunk heartbeat,
duplicate and invalid-row rejection without a partial current chunk, synthetic
crash residue, concurrent-attempt rejection, all three non-terminal expiry
states, retention, sanitized cleanup failure and retry, and preservation of
serving, ledger, capability, auth, and session rows.

The bounded-load proof used a maximum batch of 128 rows. A synthetic crash after
two committed chunks retained exactly 200 diagnostic rows and left the staging
state `LOADING`.

## Scale and rollback rehearsal

The isolated production-shape rehearsal migrated `0009` to `0010` and back to
`0009` against synthetic data:

```json
{
  "checks": {
    "empty_singleton_preserved": true,
    "five_logged_tables_created": true,
    "forward_reverse_preserved_domain": true,
    "seed_counts_match": true
  },
  "counts": {
    "channels": 86895,
    "subcatchments": 195457,
    "watersheds": 126
  },
  "forward_seconds": 0.349,
  "rollback_seconds": 0.395,
  "status": "passed"
}
```

## Final gates

The final production-server image built as:

```text
sha256:cbb52a979a1fda4c72ac745a6d33d085f75bb4c8c35cdf7dc6868549b5406619
```

```text
Ruff: passed
full Django suite: 160 passed in 39.508s
Docker/PostGIS scale acceptance: passed
```

Repository whitespace, Python compilation, documentation-link, secret, and
container-cleanup checks are recorded in the package closeout.
