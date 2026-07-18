# DB11 validation evidence

Date: 2026-07-17

Host: `forest1`

Starting revision: `0bd5dc5c735df1ba98073cab362dbf3bf5912d7f`

No release manifest, plan, credential, source data, database connection, or
production system was used.

## CLI tests

```text
release-tool CLI tests: 12 passed
image-verifier unit tests: 4 passed
```

The CLI suite covers all eight command names, the complete event envelope,
stable exit codes, verified read-only input, missing/writable/malformed input,
wrong digest, unavailable successor commands, invalid usage, and contained
unexpected errors.

## Reproducible build

Base image:

```text
python:3.12.9-slim-bookworm@sha256:48a11b7ba705fd53bf15248d1f94d36c39549903c5d59edcfa2f3f84126e7b44
```

The first direct double-build attempt failed because Docker generated different
destination-directory mtimes in otherwise identical COPY layers. Layer tar
comparison isolated that difference. The accepted script uses:

- a repository-root allowlisted context tar;
- sorted paths, numeric ownership, and epoch-zero source mtimes;
- an isolated Docker-container BuildKit builder;
- two no-cache builds;
- source-epoch timestamp rewriting during Docker export; and
- exact loaded image-ID comparison.

Both accepted builds produced:

```text
sha256:810d9f24d1020c508c80cf165013fbb2740d73a76238d23754f56b638690eb2e
```

## Image audit and execution

```json
{
  "architecture": "amd64",
  "image_id": "sha256:810d9f24d1020c508c80cf165013fbb2740d73a76238d23754f56b638690eb2e",
  "input_sha256": "17fecd1342a46ba31ed8069f69f60f42d3ad28ec051831185d833d893576108e",
  "os": "linux",
  "project_files_scanned": 1,
  "rootfs_entries": 6574,
  "status": "passed",
  "unavailable_exit": 20,
  "user": "65532:65532",
  "wrong_digest_exit": 11
}
```

The full exported root filesystem had no `.env`, Git metadata, data-release
tree, fixture, release manifest, plan, server/client tree, or source-data path.
The sole copied project file contained no credential marker. Runtime used the
immutable image ID, a read-only root filesystem, no network, and one read-only
input mount. The input was unchanged after execution.
