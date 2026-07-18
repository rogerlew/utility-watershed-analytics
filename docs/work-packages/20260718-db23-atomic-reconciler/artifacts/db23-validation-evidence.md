# DB23 validation evidence

Date: 2026-07-18

Environment: `forest1`, repository
`/workdir/utility-watershed-analytics`, branch
`agent/database-backup-deployment-spec`, starting revision
`4841648` (`Clarify DB22 execution evidence`).

Evidence mode: Mixed. Commands are Ran; contract/scope review is Static.

## Final image and tests

The production server image for the exact DB23 code built locally as:

```text
sha256:bcb69f99311516dd040facc5c798abdf5f5c69d42d353733abf5312719738f1b
```

This is a local forest1 image ID, not a published image or production
deployment authority.

Final exact-image proof:

```text
All checks passed!
No changes detected
Found 3 test(s).
Ran 3 tests in 6.136s
OK

Found 197 test(s).
Ran 197 tests in 73.955s
OK (skipped=1)
```

The one full-suite skip is the DB09 repository-schema integration inside the
production server image, which intentionally contains only `server/`. DB09
schema integration passed in the earlier mounted DB22/DB23 regression and the
standalone DB09 validator plus 12 tests passed against the exact final image
with the repository mounted. The DB08 validator plus 7 tests also passed.

## Mechanism proof

The synthetic populated base contained four watersheds, five subcatchments,
four channels, stable reviewed identities/aliases, and one SBS capability. The
target combined:

- one watershed with metadata, geometry, child, and capability changes;
- one unchanged retained watershed;
- one same-identity run replacement;
- one exact removal; and
- one addition.

The successful apply preserved matching subcatchment/channel database IDs,
preserved the retained watershed row, changed the replacement run ID while
keeping its logical identity and child IDs, retained the historical alias,
retired only the removed identity, retained unrelated content-type state, and
matched the exact target serving fingerprint and counts.

Negative snapshots proved no serving, identity, alias, capability, release, or
pointer mutation for wrong plan digest, wrong active manifest, non-READY
staging, or injected pre-pointer failure. In the two-connection test, a reader
paused after uncommitted domain mutation saw the complete old state; after the
writer committed it saw the complete target state.

## Boundary review

- `wepp3` was not contacted.
- No real release, artifact, plan, row, pointer, database, or service was
  inspected or changed.
- No credentials, `.env`, dumps, PII, real coordinates, or source data were
  recorded.
- DB23 was not committed, pushed, published, or dispatched during governed
  execution.
- Disposable DB23 PostGIS/network state was removed after acceptance; the
  validated local image was retained.
