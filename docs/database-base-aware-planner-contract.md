# Database base-aware planner contract

Status: accepted DB22 contract

Date: 2026-07-18

DB22 turns immutable DB15 release/run state into the three DB09 plan documents
needed by later reconciliation work. It is a read-only planner: generating a
plan does not stage artifacts, change serving rows, advance the active pointer,
or authorize execution.

## Preconditions

Forward planning fails unless all of these are true:

- the singleton active pointer is `ACTIVE` and exactly names the reviewed base
  release and manifest;
- the active serving-domain fingerprint recomputes to the reviewed base domain
  fingerprint;
- base and target use version 1 release, data, identity, artifact, and
  fingerprint contracts;
- both releases name the sole currently applied watershed migration and every
  run state is validated; and
- base and target use identical migration and materializer image/Git
  coordinates.

Unknown, `EMPTY`, drifted, ambiguous, unsupported, or incompatible state is an
error. The planner never substitutes the current database for the reviewed
base or treats a mismatch as a warning.

## Actions

Actions are keyed and sorted by stable `watershed_key`. Exact membership
comparison produces `add`, `change`, `remove`, or `retain`:

- run or collection replacement is an `identity` change;
- metadata, geometry, child artifacts/counts, and capability fingerprints use
  their matching DB09 change channels;
- a semantic run-fingerprint change not otherwise decomposed is an `identity`
  change; and
- a retained state must have identical before/after run and capability
  fingerprints and zero row deltas.

Run-fingerprint and classified-channel disagreement fails closed. Aggregate
row deltas are derived from the sorted actions.

The forward planner refuses a removal set greater than five watersheds or ten
percent of the reviewed base. Either threshold requires the explicit
`--allow-large-removals` option after human review; the option does not weaken
any base, compatibility, fingerprint, or schema check.

## Plan set

One generation produces:

- `forward.json`, derived from the exact populated base and target;
- `exact-inverse.json`, mechanically mirrored from the complete forward plan
  and bound to its canonical SHA-256; and
- `empty-build.json`, independently derived as all adds from literal `EMPTY`.

The empty-build plan is reconstruction proof, not authority to empty a
database. The inverse is review material for later rollback tooling, not an
executable rollback by itself.

## Command

Run from the server container/environment after the base and target ledgers
exist:

```bash
python manage.py generate_release_plans \
  --base-release-id 2026-07-18.1 \
  --target-release-id 2026-07-18.2 \
  --output-directory /review/plans
```

The output directory may exist, but none of the three filenames may already
exist. The command refuses overwrite. Output is deterministic UTF-8 JSON with
one trailing newline and conforms to `data-releases/schema/v1/plans/`.

Plan review and later execution must keep the three files together, verify the
forward canonical digest referenced by the inverse, and independently observe
the active base immediately before any mutation. DB23 owns reconciliation;
DB22 grants no production, artifact-fetch, activation, or rollback authority.
