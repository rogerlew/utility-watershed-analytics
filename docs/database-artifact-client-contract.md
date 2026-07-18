# Database artifact client and cache contract

Status: accepted version 1

Date: 2026-07-17

DB12 implements content-addressed artifact publication and caching for the
operator-owned `forest1:/wc1` filesystem. It has no cloud provider, account,
bucket, credential, role, network service, or store-deletion behavior.

## 1. Paths and identity

An `ArtifactClient` is bound to exactly one test or production namespace and
one cache root. It never selects an environment from mutable input.

Store objects use:

```text
<namespace>/objects/sha256/<first-two-hex>/<full-lowercase-sha256>
```

Cache objects use:

```text
<cache-root>/<first-two-hex>/<full-lowercase-sha256>
```

Only 64-character lowercase SHA-256 values are accepted. This prevents mutable
aliases and path traversal from becoming artifact authority. Test and production
clients use different namespace roots; absence in one never falls through to
the other.

## 2. Streaming publication

`publish(source, expected_sha256=...)` requires a non-symlink regular file. It:

1. streams bytes into a unique mode-`0600` file under the namespace `.partial`
   directory;
2. calculates SHA-256 and byte count while copying;
3. rejects an expected-digest mismatch;
4. creates private mode-`0700` content-key directories;
5. promotes with an exclusive hard link, so an existing object is never
   overwritten; and
6. verifies any existing or concurrently created object completely before
   treating publication as idempotent success.

An interruption or failure removes the exact partial file. Conflicting bytes at
the claimed digest fail with `ArtifactConflictError` and remain unchanged.

## 3. Fetch and cache recovery

`fetch(digest)` verifies every existing cache hit by hashing all bytes. A valid
hit returns immediately. A corrupt hit is atomically moved to a unique
quarantine name, then the authoritative store object is streamed into a unique
cache temporary file.

The temporary file is promoted with `os.replace` only after its full digest
matches the requested key. Successful recovery removes the quarantine. If the
store object is missing, unreadable, or corrupt, no unverified bytes are
promoted. Multiple concurrent fetchers may replace the cache with the same
verified bytes; readers never observe a partial file.

The library returns typed input, missing, permission, integrity, conflict, and
transfer failures so later CLI commands can map them to DB11's stable exit-code
classes without parsing messages.

## 4. Bounded cleanup

`cleanup_cache` is confined to exact digest files immediately below the cache
root's two-character prefix directories. It does not follow prefix or file
symlinks and has no path to the artifact store.

The caller supplies:

- retained digests;
- actively leased digests;
- maximum entry count;
- maximum total bytes; and
- optional dry-run behavior.

Candidates are deterministically ordered by modification time and digest.
Protected entries are excluded. Both limits are hard ceilings. The library has
no `delete` or `cleanup_store` API; version 1 never automates artifact-backup
deletion.

## 5. Permissions and ownership

New store/cache directories use mode `0700`; new object/cache files use `0600`.
Permission denial is fatal and distinct. This is a single-operator control,
matching DB10A; it is not an IAM or multi-user role model.

## 6. Accepted proof

The test suite covers:

- streamed publish/fetch and idempotent publication;
- interrupted publish and fetch with no promotion;
- wrong expected digest and corrupt stored bytes;
- corrupt cache quarantine and recovery;
- 16 concurrent fetches of one object;
- missing object and permission denial;
- existing-store conflict without overwrite;
- test/production namespace isolation;
- private directory/file modes and symlink confinement;
- absent store-delete methods; and
- retained/leased, entry-count, byte-count, and dry-run cleanup behavior.

The real-filesystem acceptance runner creates a temporary subtree under:

```text
/wc1/utility-watershed-analytics-artifacts/v1/test
```

It executes the same behaviors against ZFS and removes the entire temporary
subtree before success. It does not change DB10A fixtures or the production
namespace.

The artifact client is included in the code-only release-tool image. The final
DB12 forest1 double-build produced local image ID:

```text
sha256:da87d2eea21407fcc170b8928b29081be20f78501d0381e6ec6c86d0eebfff79
```

This is local acceptance evidence, not a registry-published release digest.
