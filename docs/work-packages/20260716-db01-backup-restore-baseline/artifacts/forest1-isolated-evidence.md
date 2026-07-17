# DB01 Isolated Development Evidence

Evidence mode: Ran unless marked Static

Environment: `forest1`, 2026-07-16 America/Los_Angeles

Starting revision:
`30a9077d432a5c8582759b614e0ea7224713b685` plus the package working tree

No production host, production database, external object-store account, or
accepted notification endpoint was accessed by these checks. Temporary
credentials, database dumps, restic repository data, and application secrets
are intentionally excluded from this artifact.

## Tooling

- Docker Engine 29.4.2 and Docker Compose v5.1.3.
- PostGIS test image ID:
  `sha256:7c20b0264a12a81bbad0b8adced51c4490ecbe08c8a360f44030f8109b6f6c01`.
- Restic test image: `restic/restic:0.18.0`, image ID
  `sha256:4d0ef709844dbb166a3ec66235910e7c0132d9e104d2ae889a1d75c04509cf2e`.
- ShellCheck test image: `koalaman/shellcheck:v0.10.0`.

The restic repository was a disposable local encrypted fixture. It proves the
client-side encryption and workflow boundary, not off-host durability,
provider controls, or production recoverability.

## Backup and encrypted publication

The final chain ran `scripts/run_scheduled_backup.sh` against the development
`postgis` container with a zero test-only free-space margin and a disposable
encrypted restic repository.

- Source database size: 20,720,787 bytes.
- Archive size: 75,741 bytes.
- Archive SHA-256:
  `1241d692106105ab0daed74e4031cc1f0ffdd3e5472498e5a575d29c907c454d`.
- Archive structure and full decode: passed.
- Comparison inventory: 55 tables plus roles, memberships, extensions,
  migrations, and sequences.
- Encrypted snapshot ID:
  `32655179e3865cb86fd80eee895056f477ecdd591e4b726eca39a0a68a07f0d5`.
- Repository check with 100% test-fixture data read: passed.
- Atomic `last-success` state publication after restic verification: passed.

## Restore and application smoke

`scripts/run_restore_test.sh` retrieved the newest encrypted snapshot and
created its own internal Docker network, exact-image disposable database
container, ephemeral credentials, and cleanup boundary.

- Total encrypted retrieval, database restore/comparison, and application
  smoke duration: 26 seconds.
- Test-only maximum: 120 seconds; passed. This is not an accepted production
  RTO or production-scale result.
- PostgreSQL: 17.5 (Debian 17.5-1.pgdg110+1).
- PostGIS: 3.5.2.
- Source roles and memberships: present in restore.
- Extensions, Django migrations, sequences, schema, and all table
  counts/fingerprints: exact.
- Django system and database connectivity checks: passed.
- Restored watershed-list API read: passed.
- Representative watershed detail, subcatchment, and channel checks: skipped
  by the explicit development-only empty-database allowance because external
  seed tokens were expired.
- Disposable target and anonymous volume cleanup: passed.

The first composed drill exposed a PostGIS image initialization race:
`pg_isready` briefly succeeded before the image's intentional initialization
restart. The runner now waits for the final initialization-complete marker and
then readiness; the complete rerun passed.

## Failure and retention controls

- Forced `after-local-backup` failure returned status 97.
- A complete sensitive local set was retained for diagnosis.
- Encrypted snapshot count remained 3 before and after the forced failure.
- No `last-success` state was written for the failed run.
- Missing notification webhook produced a local journal event and non-zero
  status instead of claiming external notification.
- Freshness passed with a 90,000-second maximum and failed with a forced
  one-second maximum.
- Retention rejected fewer than three exact release IDs.
- Dry-run identified an obsolete release snapshot and an older duplicate of a
  retained release.
- Apply retained exactly the newest snapshots for `release-one`,
  `release-two`, and `release-three`; remaining release-point count was 3.
- A separately copied recovery-password fixture listed all three snapshots and
  passed a 100% repository check.

## Static scheduler and repository gates

- `bash -n scripts/*.sh`: passed.
- ShellCheck for every shell script: passed.
- `python3 -m py_compile scripts/backup_retention.py`: passed.
- Ruff for `restore_smoke.py` and its tests: passed.
- `python manage.py test server.watershed.test_restore_smoke`: 3 tests passed.
- Live development `python manage.py restore_smoke --allow-empty`: passed.
- `systemd-analyze verify ops/systemd/*.service ops/systemd/*.timer`: passed;
  it emitted one unrelated warning for the pre-existing executable host unit
  `/etc/systemd/system/docker-compose-fswepp2.service`.
- All four timer calendar expressions normalized successfully.
- Each timer declares `Persistent=true` (Static). An actual reboot was not
  authorized on the shared development host.
- `git diff --check`: recorded in final package gates.

## Unmet DB01 completion evidence

- accepted project-owned off-host provider and bucket controls;
- named online and recovery key owners;
- accepted production maximum RTO and production-shaped capacity;
- accepted external notification channel and delivered failure alert;
- actual missed-timer/reboot execution;
- production-compatible non-empty restore with representative API reads; and
- production scheduled cycle or production access of any kind.
