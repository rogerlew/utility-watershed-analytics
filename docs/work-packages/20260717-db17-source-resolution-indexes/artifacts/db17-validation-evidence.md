# DB17 validation evidence

Date: 2026-07-17

Host: `forest1`

Starting revision: `319bf717d570cb42356ef5e4b88f90e60c612ba2`

Evidence mode: Mixed

No production host, production namespace, credential, real release member,
real source data, or mutable external upstream was accessed.

## Focused tests

```text
release-tool CLI, artifact, and source tests: 40 passed
source-acceptance and image-verifier tests: 6 passed
artifact-acceptance wrapper: 1 passed
```

Source tests cover standalone and batch success, explicit custom master URL,
empty master, missing/extra/duplicate members, missing required source, declared
partial transfer, malformed and non-finite GeoJSON, malformed Parquet, secret
containment, descriptor/receipt drift, deterministic output, and receipt replay
with zero upstream reads. Existing DB11 and DB12 behavior remains covered.

Both generated standalone and batch documents passed the actual DB08 Draft
2020-12 `batch-member-index` schema and semantic validator using the repository's
pinned `jsonschema==4.23.0` environment.

## Forest1 acceptance

Workspace parent:

```text
/wc1/utility-watershed-analytics-artifacts/v1/test
```

Sanitized result:

```json
{
  "batch_source_count": 6,
  "checks": {
    "batch_exact_member": true,
    "custom_master_used": true,
    "receipt_replay_byte_identical": true,
    "standalone_exact_member": true
  },
  "immutable_object_count": 9,
  "standalone_source_count": 6,
  "status": "passed",
  "temporary_subtree_removed": true
}
```

DB17 temporary-subtree counts were zero before and after execution. Existing
test fixtures and the production namespace were untouched.

## Reproducible image

Both final no-cache normalized builds produced:

```text
sha256:8332c517002e819ead3dbaf2480fe479209175d0365ad5e92010f854c08e89ce
```

Image audit result:

```json
{
  "architecture": "amd64",
  "artifact_module_imported": true,
  "image_id": "sha256:8332c517002e819ead3dbaf2480fe479209175d0365ad5e92010f854c08e89ce",
  "os": "linux",
  "project_files_scanned": 5,
  "rootfs_entries": 6580,
  "source_module_imported": true,
  "status": "passed",
  "unavailable_exit": 20,
  "user": "65532:65532",
  "wrong_digest_exit": 11
}
```

The image contains only the CLI, artifact client, and source preparer package;
it contains no descriptor, member index, receipt, fixture, credential, source
data, repository metadata, server, or client tree.

## Repository gates

Python compilation, Ruff 0.14.1, workflow YAML parsing, changed-document links,
secret-pattern review, executable mode, whitespace checks, and
`git diff --check` passed. DB17 was not committed or pushed, matching the
package authority.
