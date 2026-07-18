# DB12 validation evidence

Date: 2026-07-17

Host: `forest1`

Starting revision: `722d414e3b30f7f51382da4c7b3afd66ab737fe6`

No cloud provider, credential, production namespace, database, real release
artifact, or production server was accessed.

## Focused tests

```text
release-tool CLI and artifact tests: 29 passed
artifact acceptance-wrapper tests: 1 passed
image-verifier tests: 4 passed
```

Seventeen artifact client/cache cases cover streaming and idempotent publish,
streaming fetch, interrupted publish/fetch, wrong expected digest, corrupt store,
corrupt cache recovery, 16 concurrent fetches, missing object, permission denial,
store conflict, namespace isolation, private modes, symlink confinement, absent
store deletion, and retained/leased bounded cleanup.

## Forest1 acceptance

Workspace parent:

```text
/wc1/utility-watershed-analytics-artifacts/v1/test
```

Sanitized result:

```json
{
  "checks": {
    "conflict_rejected": true,
    "corrupt_cache_recovered": true,
    "interrupted_fetch_rejected": true,
    "missing_object_rejected": true,
    "namespace_isolated": true,
    "permission_denied": true,
    "store_delete_api_absent": true,
    "wrong_checksum_rejected": true
  },
  "cleanup_entries": 1,
  "concurrent_fetches": 16,
  "fixture_bytes": 2031616,
  "fixture_sha256": "1bfeea7a30a04e141d75d4753d05f20bd4850ebb116129630885198ae8049ca9",
  "status": "passed",
  "temporary_subtree_removed": true
}
```

Temporary acceptance-subtree counts were zero before and after execution. The
existing DB10A fixtures and production namespace were untouched.

## Reproducible image

Both final no-cache normalized builds produced:

```text
sha256:da87d2eea21407fcc170b8928b29081be20f78501d0381e6ec6c86d0eebfff79
```

Image audit result:

```json
{
  "architecture": "amd64",
  "artifact_module_imported": true,
  "image_id": "sha256:da87d2eea21407fcc170b8928b29081be20f78501d0381e6ec6c86d0eebfff79",
  "os": "linux",
  "project_files_scanned": 4,
  "rootfs_entries": 6579,
  "status": "passed",
  "unavailable_exit": 20,
  "user": "65532:65532",
  "wrong_digest_exit": 11
}
```

The image contains the CLI and artifact client package, but no release manifest,
plan, credential, source data, repository metadata, server, or client tree.
