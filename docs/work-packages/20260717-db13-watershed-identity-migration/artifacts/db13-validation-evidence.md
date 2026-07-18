# DB13 validation evidence

Date: 2026-07-17

Host: `forest1`

Starting revision: `ee9e70b54530300cea1b58e418436b3f35128856`

No production server, production database, source API, real release artifact,
credential, user record, or external service was accessed. Every database was a
disposable PostGIS container on an isolated Docker network.

## Focused behavior

Final focused result:

```text
tests: 12
result: passed
```

The suite covers:

- unique stable watershed keys and one current alias per identity;
- permanent run-alias collision rejection;
- current and historical run-ID route compatibility;
- stable-key watershed, subcatchment, and channel routes;
- DB07 stable serialized child feature IDs;
- retired 410 and unknown 404 behavior;
- aggregate complete/missing/mismatched logical-link validation;
- exact accepted standalone key assignment without batch-key inference;
- expand/backfill of aliases and child links;
- old model-state reads against the expanded schema;
- exact pre-write reverse migration with child ID preservation; and
- fail-closed reverse migration after identity-aware alias writes.

## Production-shaped rehearsal

The disposable fixture matched the accepted DB06 aggregate row shape. It used
synthetic identifiers and one synthetic geometry; no production row values were
used.

```json
{
  "checks": {
    "forward_preserved_child_ids": true,
    "identity_validation_passed": true,
    "old_code_reads_expanded_schema": true,
    "rollback_preserved_child_ids": true,
    "rollback_preserved_counts": true,
    "seed_counts_match": true
  },
  "counts": {
    "channels": 86895,
    "subcatchments": 195457,
    "watersheds": 126
  },
  "forward_seconds": 15.268,
  "identity_counts": {
    "assigned_watershed_keys": 0,
    "channels": 86895,
    "identities": 126,
    "run_aliases": 126,
    "subcatchments": 195457,
    "watersheds": 126
  },
  "rollback_seconds": 12.631,
  "status": "passed"
}
```

The zero assigned keys are expected because the scale fixture uses synthetic
unreviewed run IDs. Exact assignment behavior is covered by focused migration
fixtures.

## Full server gate

The final production image ran the repository's complete server test command
against fresh disposable PostGIS:

```text
tests: 127
result: passed
```

Final image:

```text
sha256:7b003752cb14bb3c08ad0356aa0ec2bec67c0b6d1a98ffd4d8c0b182e0db7e17
```

Ruff passed. `makemigrations --check --dry-run` reported no changes; because
that specific dry run intentionally had no database container, Django also
emitted its non-fatal unreachable-host migration-history warning.

## Client compatibility gate

Assigned legacy browser routes now redirect to the canonical stable-key route.
The stable route resolves `current_runid` from the stable-key API response and
provides it through a narrow context, so existing source-run analytics and
external links do not confuse stable keys with upstream run IDs. Unassigned
legacy routes remain available until their reviewed key assignment.

```text
production build: passed
lint: passed
type check: passed
test files: 40 passed
tests: 583 passed
```

Final client image:

```text
sha256:09f1adc870d3301575b4099b446fdabb18e664e41551e0d710a20468975d68a5
```

Documentation relative links and fences, Python syntax, secret-assignment scan,
tracked and untracked changed-file whitespace, `git diff --check`, and final
container-cleanup checks passed. No DB13 container remained running.
