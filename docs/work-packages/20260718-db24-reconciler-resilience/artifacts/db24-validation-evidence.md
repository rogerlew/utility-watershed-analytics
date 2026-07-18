# DB24 validation evidence

Date: 2026-07-18

Environment: `forest1`, repository
`/workdir/utility-watershed-analytics`, branch
`agent/database-backup-deployment-spec`, starting revision
`d2d209a` (`Complete DB23 atomic reconciler`).

Evidence mode: Mixed. Commands are Ran; contract/scope review is Static.

## Final image and tests

The production server image for the exact DB24 server code built locally as:

```text
sha256:004778460412e099f4d2ebc00f00edc116db5d4f7c7313f4869c004ea34ed3db
```

This is a local forest1 image ID, not a published image or production
deployment authority.

Final exact-image proof:

```text
All checks passed!
No changes detected

Found 17 test(s).
Ran 17 tests in 25.586s
OK

Found 201 test(s).
Ran 201 tests in 86.771s
OK (skipped=1)
```

The one full-suite skip is the DB09 repository-schema integration inside the
production server image, which intentionally contains only `server/`. The DB08
validator plus 7 tests and DB09 validator plus 12 tests passed against the exact
image with the repository mounted. The combined DB16/DB20–DB24 regression
passed 32 tests in 49.105 seconds.

## Mechanism proof

An exact-active verification snapshot proved no change to the active pointer,
activation timestamp, serving rows, capabilities, artifacts, releases,
attempts, or staging. The verifier recomputed the exact ledger fingerprint and
counts and created no attempt; therefore a later orchestrator can call it
before artifact work or backup and return on a verified no-op.

Synthetic forward activation followed by its canonical exact inverse restored
the complete prior serving/capability fingerprint. The rollback required the
failed target to be the active reviewed base, complete prior-release staging,
matching reviewed/actual inverse digests, and the exact source forward plan. A
modified forward binding failed without mutation.

An injected final-fingerprint failure after pointer activation but before
transaction commit restored the complete pre-attempt snapshot. Existing DB23
negative and reader tests cover staging, lock/base, and activation failures.
The recovery management command terminalized an expired attempt, released its
lease, emitted sanitized JSON, and retained staging under DB16 policy.

Finally, an independent DB20 EMPTY build and DB23 populated reconciliation to
the same target produced identical accepted domain/capability fingerprints and
row counts. Canonical simplified geometry is now derived consistently by both
paths.

## Boundary review

- `wepp3` was not contacted.
- No real release, artifact, plan, row, pointer, database, service, or backup
  was inspected or changed.
- No credentials, `.env`, dumps, PII, real coordinates, or source data were
  recorded.
- DB24 was not committed, pushed, published, or dispatched during governed
  execution.
- Disposable DB24 PostGIS/network state was removed after acceptance; the
  validated local image was retained.
