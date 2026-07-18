# Database artifact backup contract

Status: accepted version 1, amended by DB10A

Date: 2026-07-17

This contract follows the operator's authoritative decision to keep artifact
backups on existing project infrastructure at `forest1:/wc1`. No paid storage
provider, cloud account, bucket, access key, or network storage service is part
of version 1.

## 1. Storage decision

The artifact backup root is:

```text
/wc1/utility-watershed-analytics-artifacts/v1
```

`forest1` provides the existing ZFS-backed `/wc1` filesystem. DB10A observed
about 1.1 TB free at acceptance. This is adequate for the current project, but
it is one host and one storage pool, not a geographically independent copy.

Database backups remain separate at:

```text
/wc1/utility-watershed-analytics-db-backups
```

The artifact backup tree has `test` and `production` namespaces. The production
namespace remains empty until a later authorized release package copies an
accepted release into it.

## 2. Ownership and access

This is a single-operator system owned by `roger`. There are no application
users, accounts, PII, cloud roles, or storage credentials to manage.

- directories use mode `0700`;
- files use mode `0600`;
- no public or group access is accepted; and
- no application process receives deletion automation.

These permissions prevent unintended access by other host users. They do not
protect against the operator or a privileged host process, so integrity checks
and restore rehearsal remain required.

## 3. Content layout and copy behavior

Objects use their full SHA-256 digest as identity:

```text
objects/sha256/<first-two-hex>/<full-lowercase-sha256>
```

A copy writes to a unique temporary file in the destination directory, verifies
the digest, and promotes without overwriting an existing object. An existing
object is accepted only when its bytes match its key. Partial copies and digest
collisions fail closed.

Release manifests name exactly the active release and two rollback releases.
Mutable aliases are never authority.

## 4. Retention and deletion

The active release plus `rollback-1` and `rollback-2` have no automatic TTL.
Version 1 has no scheduled deletion or lifecycle service. Any later cleanup is
manual, previews exact unreachable objects, and is outside an active build or
restore.

This deliberately favors simple recovery over storage optimization.

## 5. Verification and restore

Every accepted backup records a deterministic inventory of release roles,
object sizes, and SHA-256 digests. Verification checks every manifest and every
referenced object after copy and after restore.

The repository tool is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/accept_artifact_backup.py \
  --root /wc1/utility-watershed-analytics-artifacts/v1
```

It provisions the private namespaces, performs an idempotent three-release test
backup, rejects partial/conflicting/corrupt/unavailable-path cases, and restores
the test backup into a clean temporary directory. It never writes real
production artifacts.

Run the clean restore rehearsal quarterly and before relying on this backup for
a production data release.

## 6. Capacity and failure behavior

The tool requires at least 100 GiB free before copying. A full filesystem,
unavailable path, digest mismatch, missing object, or permission error exits
nonzero and leaves the source and active release unchanged. External alerting is
not required for this single-operator version; the command result is the
operator-visible signal.

The authoritative machine-readable policy and failure review are:

- `data-releases/storage-contract/v1/artifact-store-policy.json`; and
- `data-releases/storage-contract/v1/threat-review.json`.

## 7. DB10A acceptance

DB10A is complete only after the real `forest1:/wc1` path is observed with:

- private test and production namespaces;
- three content-addressed fixture releases copied and verified;
- exact clean restore verification;
- partial copy, collision, corruption, missing object, unavailable path, and
  capacity checks;
- repeat execution without changing accepted bytes; and
- confirmation that database backups remain separate and unchanged.
