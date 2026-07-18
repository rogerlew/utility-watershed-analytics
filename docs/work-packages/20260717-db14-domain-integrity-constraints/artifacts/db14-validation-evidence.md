# DB14 validation evidence

Date: 2026-07-17

Host: `forest1`

Starting revision: `907cd7e191da7a4501908653611caf273fb64527`

No production host, database, source API, real release artifact, credential,
or user record was accessed. All database evidence used disposable PostGIS on
an isolated Docker network with synthetic identifiers and geometry.

## Focused behavior

The focused database, loader, aggregate-audit, and migration suite passed 15
tests. It covers stable-key and status checks, compatibility and logical child
uniqueness, old/logical orphan rejection, aggregate migration preflight,
Topaz-column spelling and ambiguity handling, exact rebuild ownership, ORM and
raw-database deletion behavior, and preservation of identity/auth/session
state.

`makemigrations --check --dry-run` reported no model drift. Ruff passed.

## Production-shaped rehearsal

The isolated fixture matched the accepted DB06 aggregate row counts. The
forward migration installed all seven named constraints and the reverse
migration removed them without changing serving counts or sampled child IDs.

```json
{
  "checks": {
    "constraints_installed": true,
    "duplicate_subcatchment_rejected": true,
    "forward_preserved_child_ids": true,
    "forward_preserved_counts": true,
    "invalid_collection_rejected": true,
    "locks_observed": true,
    "orphan_channel_rejected": true,
    "rebuild_preserved_non_domain": true,
    "rollback_preserved_non_domain": true,
    "seed_counts_match": true
  },
  "counts": {
    "channels": 86895,
    "subcatchments": 195457,
    "watersheds": 126
  },
  "forward_seconds": 2.128,
  "lock_samples": 669,
  "rollback_seconds": 0.213,
  "status": "passed"
}
```

Observed granted lock modes included `AccessShareLock`, `ShareLock`, and
`AccessExclusiveLock` on the constrained watershed-domain relations. This is
measurement evidence for later production planning, not production migration
authority or a guaranteed production duration.

The rebuild probe deleted only channel, subcatchment, and watershed rows inside
a rolled-back transaction. The fixture's 126 identities, 126 aliases, one auth
user, and one session remained present during the probe and after migration
rollback.

## Container evidence

The production server image containing the acceptance harness was:

```text
sha256:dce9341b992435712845784d202332e99bd1c42aa07c94191d0da17118c00478
```

## Full server and repository gates

The final production image passed Ruff, migration drift checking, and all 138
server tests against fresh disposable PostGIS. The migration drift command
reported `No changes detected` plus the expected non-fatal warning because
that command intentionally had no database container.

Python syntax, documentation links and fences, secret-assignment scan,
tracked/untracked whitespace, `git diff --check`, and disposable-container
cleanup passed. No DB14 container remained running.
