# DB22 validation evidence

Date: 2026-07-18

Environment: `forest1`, repository
`/workdir/utility-watershed-analytics`, branch
`agent/database-backup-deployment-spec`, starting revision
`c410628` (`Complete DB21A legacy base tooling`).

Evidence mode: Mixed. Commands are Ran; contract/scope review is Static.

## Final image and tests

The production server image for the exact DB22 code built locally as:

```text
sha256:53d95a80ba511358f1533f9a58c0a61271c0f66b15f2fdb50e2dc7274550f9c6
```

This is a local forest1 image ID, not a published image or production
deployment authority.

Focused DB22 proof with the repository mounted so the generated documents were
validated against the native DB09 schemas:

```text
All checks passed!
Found 6 test(s).
Ran 6 tests in 1.821s
OK
```

Final exact-image regression:

```text
All checks passed!
No changes detected
Found 194 test(s).
Ran 194 tests in 65.759s
OK (skipped=1)
```

The one skip is the DB09 repository-schema integration inside the production
server image, which intentionally contains only `server/`. The same test
passed in the mounted focused run. The standalone DB08 and DB09 validators and
their 7 and 12 tests also passed inside the final image with the repository
mounted. A first host-Python attempt could not start because host Python lacks
the pinned `jsonschema` package; no gate was omitted.

## Mechanism proof

Synthetic populated base/target fixtures proved:

- exact active release/manifest and recomputed domain-fingerprint assertion;
- metadata-only, geometry, capability, and same-watershed run-replacement
  classification;
- batch expansion and reviewed shrink with exact retain/remove state;
- refusal of unknown active, serving drift, changed materializer, changed
  migration, and unexpected large removals;
- byte-identical repeated generation, schema-valid forward/inverse/EMPTY
  documents, mechanical inverse deltas/state, and independently all-add EMPTY
  planning; and
- no release, watershed, or child-row mutation during planning.

## Boundary review

- `wepp3` was not contacted.
- No production release, artifact, plan, row, pointer, or service was inspected
  or changed.
- No credentials, `.env`, dumps, PII, real coordinates, or source data were
  recorded.
- DB22 was not committed, pushed, published, or dispatched during governed
  execution.
- Disposable DB22 PostGIS/network state was removed after acceptance; the
  validated local image was retained.
