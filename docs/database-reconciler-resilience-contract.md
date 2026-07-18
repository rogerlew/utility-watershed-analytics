# Database reconciler resilience contract

Status: accepted DB24 contract

Date: 2026-07-18

DB24 closes the DB23 reconciler's no-op, failure, recovery, rollback, and
disaster-rebuild boundaries. It does not implement the production deployment
orchestrator, perform a backup, or authorize production activation.

## Verified no-op boundary

`verify_active_release_noop` in
`server/server/watershed/reconciliation.py` locks and reads the singleton
active-release row, verifies the exact release and manifest, recomputes the
serving-domain fingerprint and row counts, and verifies capability count. A
successful result is an exact active-release verification, not a new release
attempt.

The verifier writes no domain, capability, pointer, release, attempt, staging,
artifact, timestamp, or backup state. A later deployment orchestrator must run
this verification before attempt creation, artifact work, or backup and return
immediately when it succeeds. Audit or report output may append outside this
database boundary.

## Failure and recovery matrix

| Boundary | Failure behavior | Recovery |
| --- | --- | --- |
| Preparation | Missing, corrupt, or mismatched immutable input fails before staging or activation. | Correct the input and begin a separately reviewed attempt. |
| Staging | Capacity, lease, parsing, count, or completeness failure leaves the active release unchanged. | Use the DB16 retention/cleanup policy; restage in a new or still-valid attempt as applicable. |
| Lock and base recheck | Wrong active release, manifest, fingerprint, counts, plan, or incomplete staging fails after locks and before mutation. | Re-plan from the observed active base and obtain review again. |
| Activation | Any keyed domain, child, identity, alias, capability, or pointer error rolls back the transaction. | Inspect the sanitized failed attempt, correct the cause, and retry through a reviewed attempt. |
| Post-activation validation | A final target fingerprint or count mismatch occurs before commit and rolls back the pointer and all serving changes. | Treat it as an activation failure; do not accept or manually advance the target. |
| Exact rollback | Wrong current target, broken forward binding, wrong inverse digest, incomplete prior staging, or final prior fingerprint mismatch rolls back without mutation. | Re-establish the exact retained forward/inverse documents and complete prior-release staging before retrying. |

No failure path authorizes an unreviewed plan, manual serving-row repair, or a
blind pointer change.

## Expired attempts

Run the bounded recovery command from the server container:

```bash
python manage.py recover_release_attempts
```

The command reuses DB16 recovery. It terminalizes expired nonterminal attempts,
releases their lease, emits sanitized JSON, and applies the existing staging
retention policy. Diagnostic rows remain until `retention_until`; due rows are
cleaned, and cleanup failure remains explicit and retryable. Recovery does not
change the active serving release.

## Exact inverse rollback

`rollback_and_activate_release` uses the same DB20 staging and DB23 atomic
mutation path as a forward reconciliation. It accepts only an `exact-inverse`
plan whose canonical digest matches the reviewed and actual attempt digests and
whose complete source forward plan regenerates that inverse exactly.

The rollback attempt's reviewed base must be the failed target currently named
by the active pointer. The prior release is staged as the complete target, and
the reconciler reasserts the current base, plan direction, row counts, and final
prior-release fingerprint inside the activation transaction. A successful
inverse restores the prior accepted serving-domain and capability fingerprint;
any mismatch leaves the failed target wholly active.

## Disaster rebuild equivalence

A rebuild from `EMPTY` uses DB20's strict materializer and the same canonical
serving-row conversion used by DB23. For one accepted target release, a clean
build and populated reconciliation must produce identical bounded domain and
capability fingerprints and row counts. This is state equivalence, not a claim
that database-generated row IDs or audit history are identical.

DB25 may now add deployment serialization and compatibility checks. DB26 owns
the later production orchestration, including calling the verified no-op gate
before backup and using the recovery and exact rollback paths defined here.
