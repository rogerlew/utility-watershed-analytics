# DB21A validation evidence

Date: 2026-07-18

Environment: `forest1`, repository
`/workdir/utility-watershed-analytics`, branch
`agent/database-backup-deployment-spec`, starting revision
`2d6eacb` (`Complete DB21 clean-build validation`).

Evidence mode: Mixed. Commands are Ran; contract/scope review is Static.

## Final image and tests

The final production server image built successfully:

```text
sha256:f17237f1d5ad0980901f9f1f9040b5d1ee03aa40b9b947d1e59c042e1698b565
```

This is a local image ID for the exact DB21A tree, not a published digest or
production authority.

Focused DB20/DB21/DB21A proof against disposable PostGIS:

```text
All checks passed!
Found 15 test(s).
Ran 15 tests in 17.643s
OK
```

Final exact-image regression:

```text
All checks passed!
No changes detected
Found 188 test(s).
Ran 188 tests in 62.974s
OK
```

## Mechanism proof

The production-shaped synthetic fixture contained two populated watersheds,
four subcatchments, two channels, stable reviewed identities/aliases, one SBS
bootstrap capability, an immutable capability index, and its runtime raster.

- Export wrote the manifest and every ordinary/capability object by SHA-256.
- The manifest was reloaded from its immutable object rather than reused from
  memory.
- After deleting the synthetic source rows, DB20/DB21 rebuilt solely from the
  export with exact main/simplified geometry, metadata, child fields, counts,
  domain fingerprint, and capability fingerprint.
- Adoption activated the baseline without changing pre-existing domain row
  IDs, values, relationships, or unrelated content-type rows.
- Rollback removed exactly one bootstrap capability, restored coherent `EMPTY`,
  retained ledger/audit history, and left the same pre-existing snapshots.
- Identity membership, artifact checksum, current migration, and post-export
  semantic fingerprint mismatches failed with no ledger, capability, attempt,
  pointer, or additional domain mutation.

## Boundary review

- `wepp3` was not contacted.
- No actual production row, identity mapping, artifact, `/wc1` production
  namespace, database, pointer, or service was inspected or changed.
- No credentials, `.env`, dumps, PII, or source data were recorded.
- DB21A was not committed, pushed, published, or dispatched.
- Disposable Docker/PostGIS state was removed after acceptance; the validated
  local image was retained.
