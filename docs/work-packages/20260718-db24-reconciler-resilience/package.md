# DB24 — Reconciler resilience and rollback

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB24`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, synthetic forward/inverse
plans, disposable PostGIS, injected faults, attempt recovery, and clean-build
comparison on forest1. It excludes `wepp3`, real releases/artifacts/plans,
production backup/activation/rollback, commit, push, PR, and workflow dispatch.

## Objective

Close DB23's no-op, failure, recovery, exact-inverse rollback, and disaster
rebuild boundaries without introducing the later production orchestrator.

## Decisions

- Verify an already-active exact target before attempt creation, artifact work,
  or backup; the verifier is strictly read-only.
- Apply an exact inverse only with its complete source forward plan, canonical
  digest binding, exact currently active failed target, and complete staging of
  the prior release.
- Reuse DB16 expired-attempt recovery and expose one small management command;
  do not create another lease state machine.
- Treat final fingerprint validation as part of activation, so even a
  post-pointer pre-commit failure rolls back the entire transaction.
- Use DB20's EMPTY writer for disaster rebuild and compare its accepted target
  fingerprint with populated reconciliation to the same release.

## Gates

- `git diff --check`, Ruff, migration drift, focused DB24 tests, and complete
  server suite in the final production image.
- DB08/DB09 and DB20–DB23 regression.
- Exact active no-op leaves pointer timestamp, serving rows, capabilities, and
  artifacts unchanged.
- Missing/pre-activation, lock/base, activation, post-activation, and rollback
  faults preserve the prior committed release.
- Expired attempt recovery releases the lease and retains/cleans staging per
  DB16 policy.
- Exact inverse restores prior serving fingerprint and rejects the wrong active
  target or broken forward binding.
- EMPTY disaster rebuild and populated reconciliation reach identical accepted
  target fingerprints.
- Documentation, scope, secrets, links, and disposable cleanup.

## Execution record

- Added a strictly read-only exact-active verifier that rechecks release,
  manifest, domain fingerprint, row counts, and capability count without
  creating an attempt or changing pointer, timestamp, serving, artifact, or
  backup state.
- Bound exact inverse application to its canonical reviewed digest and complete
  source forward plan, reasserted the currently active failed target, and reused
  DB20 staging plus DB23's atomic mutation and final-fingerprint path.
- Exposed DB16 expired-attempt recovery as a small sanitized management command
  while retaining its existing lease release, diagnostic retention, cleanup,
  retry, and active-state preservation behavior.
- Injected a post-pointer pre-commit fingerprint failure and proved complete
  transactional rollback. Broken inverse binding also failed without mutation.
- Corrected the ordinary EMPTY writer to derive canonical simplified geometry,
  then proved a clean DB20 rebuild and populated DB23 reconciliation reach the
  identical accepted target serving/capability fingerprint.
- Passed 32 combined DB16/DB20–DB24 tests and all 201 server tests in the final
  production image, plus DB08/DB09 validators and tests.
- Used synthetic rows and disposable PostGIS only. No `wepp3`, real release,
  production backup/activation/rollback, commit, push, PR, or workflow dispatch
  occurred during DB24 execution.

### Commands and evidence

| Gate | Result |
| --- | --- |
| Final production image build | Passed; `sha256:004778460412e099f4d2ebc00f00edc116db5d4f7c7313f4869c004ea34ed3db` |
| Ruff and migration drift | Passed; no changes detected |
| Focused DB16/DB24 recovery and resilience proof | 17 passed in 25.586 seconds |
| Combined DB16/DB20–DB24 regression | 32 passed in 49.105 seconds |
| Final-image server regression | 201 passed in 86.771 seconds; one DB09 repository-schema integration skipped because schemas are outside the server image |
| DB08 schema contract | Validator plus 7 tests passed |
| DB09 fingerprint/plan contract | Validator plus 12 tests passed |

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met
- Blocker: none
- First follow-on action: scaffold DB25 deployment serialization
- Successor package: DB25, not yet scaffolded

## Artifacts

- `artifacts/db24-validation-evidence.md`
- `docs/database-reconciler-resilience-contract.md`

## Closeout checklist

- [x] Package status/evidence mode are accurate.
- [x] Gates and skipped reasons are recorded.
- [x] Evidence contains no credentials, real coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match authority.
