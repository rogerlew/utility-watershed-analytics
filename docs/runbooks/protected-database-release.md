# Protected Database Release

Status: accepted DB27 repository contract; GitHub settings and production
installation remain unapplied

DB27 adds the approval and status path around DB26. It does not authorize a
workflow dispatch, production access, database change, systemd start, GitHub
setting change, or secret installation. `forest1` remains the artifact,
inventory, database-backup, and private status host. `wepp3` remains
production.

This is deliberately simple for one operator. The same person can prepare,
approve, and operate a release in sequence, but each step is separate and
leaves an exact hash-bound record.

## Four roles

| Role | Mechanism | Can do | Cannot do |
| --- | --- | --- | --- |
| Preparer | `data-release-prepare.yml` on GitHub-hosted CI | Run contract/clean-build CI and package reviewed files | Access production environment, runner, host, or secrets |
| Approver | Required reviewer on `production-data-deploy` | Review preparation run, artifact name, operation ID, source commit, and authorization SHA-256 | Change the reviewed bundle after approval |
| Deployer | Self-hosted `deploy` runner plus root DB26 unit | Verify, install the immutable request, and start the durable unit | Prepare or silently substitute inputs |
| Rollback operator | Required reviewer on `production-data-rollback` and distinct rollback workflow | Authorize a separately prepared rollback bundle | Use the deploy authorization or bypass exact hashes |

GitHub environment reviewers are approval gates, not standing production
authority. Every production dispatch still needs the operator to review the
specific release, impact, backup, rollback, and timing.

## Required GitHub settings

These settings are not created by repository code. Configure them in a later
authorized administrative task before the first dispatch:

1. Create `production-data-deploy` with a required reviewer and restrict it to
   the protected deployment branch/tag policy.
2. Create `production-data-rollback` separately with a required reviewer and
   the same branch/tag restriction.
3. Put no secrets in either environment. DB26 reads already-installed,
   root-owned minimized credentials on `wepp3`.
4. Allow the production runner identity to use only the documented `sudo
   systemctl start utility-watershed-analytics-database-deploy@...` and bundle
   installation commands. DB27A owns that production setup.
5. Configure a read-only runner on `forest1` with label `data-status` and the
   five `DATA_RELEASE_*` repository variables used by the status workflow.

Environment settings and runner permissions must be captured in a sanitized
administrative record under `docs/sys-administration`; never place reviewer
tokens, runner tokens, credentials, or raw environment exports in Git.

## Prepare

Run **Prepare Database Release** manually with action `deploy` or `rollback`
and repository-relative paths to the DB26 request, DB08 release/member
documents, DB22 forward/inverse plans, accepted clean-build report, and
inventory snapshot. Preparation reuses server clean-build and data-contract
CI, reads no secret, and cannot use a self-hosted runner.

`scripts/release_authorization.py prepare` verifies the target release,
manifest, request coordinates, all four source hashes, clean-build result, and
inventory counts. It emits a deterministic mode-private bundle containing
only fixed filenames plus `authorization.json`. Record the preparation run ID,
artifact name, exact source commit, operation ID, action, and authorization
SHA-256 shown in `preparation-result.json`.

GitHub's workflow artifact is the protected handoff, not the authoritative
backup. The accepted long-lived artifact and database backup roots remain on
`forest1:/wc1`. The SHA-256 makes deletion or substitution detectable; the
workflow artifact retention is 90 days.

## Deploy or roll back

**Deploy Database Release** and **Roll Back Database Release** are distinct
manual-only workflows. Neither has `push`, `pull_request`, or `schedule`, so a
merge cannot deploy watershed data. Both use DB25's non-cancelling
`utility-watershed-analytics-production` concurrency group.

Before approving, compare all five protected inputs with the preparation
result. The job downloads only the named artifact from the named preparation
run, checks out the exact source commit, makes downloaded files read-only, and
verifies every byte and the fixed action. It fails before installation for a
wrong hash, operation, commit, action, filename, extra file, symlink, writable
file, mismatched report, or mutable input.

After verification the job installs the request under the operation ID and
starts `utility-watershed-analytics-database-deploy@OPERATION.service`.
Systemd, not the Actions client, owns execution. DB26 handles locking, backup,
activation, smoke, exact rollback, resume, archive, and cleanup. The workflow
retains verification and terminal reports even when the unit fails. DB26 also
copies the terminal report to
`forest1:/wc1/utility-watershed-analytics-db-deployment-reports`.

## Public status

`GET /api/watershed/release-status/` returns only:

- schema version and `EMPTY`/`ACTIVE` state;
- active release ID, manifest SHA-256, data-contract version, and activation
  time; and
- aggregate watershed, subcatchment, channel, and capability counts.

It does not expose attempts, failures, leases, backup IDs/ages, storage paths,
credentials, runner details, or row-level data.

## Private monitoring

`data-release-status.yml` runs every six hours and manually on the read-only
`forest1` status runner. The runner captures the public endpoint and reads four
private inputs:

- accepted inventory snapshot, including artifact publication time;
- current `/wc1` capacity and artifact-size snapshot plus the prior size;
- latest verified restic publication receipt; and
- a sanitized attempt-state mirror maintained by the restricted status
  collector.

Start from `ops/database-deployment/status/*.example`. Snapshot collection is
a small host-administration task: keep files mode `0600`, write them atomically,
and point repository variables at their absolute forest1 paths. Do not give the
status runner backup passwords or write access to artifacts, backups, attempts,
or production.

`scripts/check_database_release_status.py` fails on active/inventory mismatch,
count mismatch, less than 100 GiB free, more than 100 GiB growth between
snapshots, artifact age over 31 days, backup age over 25 hours, any retained
failed/rollback-failed attempt, or a nonterminal attempt unchanged for more
than two hours. Its mode-`0600` sanitized report is retained for 90 days.
Workflow failure is the current single-operator alert; no paid monitoring or
storage provider is added.

## Rehearsal before production

Before DB33, exercise the exact workflows against a disposable staging host:

1. prepare deploy and rollback bundles for the same synthetic release pair;
2. reject wrong environment, action, operation, source commit, artifact, and
   authorization hash;
3. approve deploy, sever the Actions client, and observe DB26 finish from
   systemd state/report;
4. prove the public active status equals the database and inventory snapshot;
5. inject backup, stale-base, smoke, failed-attempt, abandoned-attempt, storage,
   and age failures; and
6. approve only the distinct rollback path and retain both reports.

No production release should be proposed until the GitHub settings, runner
permissions, installed DB26 phase bundle, status snapshots, and DB27A schema/
code compatibility rollout are all separately accepted.
