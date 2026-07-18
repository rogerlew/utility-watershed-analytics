# DB18 validation evidence

Date: 2026-07-17

Host: `forest1`

Starting revision: `bea4a99ca30938b145c6546fcf64ea362a9f59fb`

Evidence mode: Mixed

No real NASA target, real enrichment source, real member mapping, credential,
production host, production namespace, or production data was accessed.

## Focused tests

```text
release-tool CLI, artifact, source, and enrichment tests: 47 passed
acceptance and image-verifier wrapper tests: 9 passed
```

Seven DB18 tests cover deterministic positive joining, matched and both
unmatched sides, target/source missing and null join keys, target/source
duplicates, missing approved fields, conflicting existing values, wrong target
prefix, source size/hash mismatch, post-transform geometry/run-ID/join-key/
member-count/other-property mutations, fourteen fixed lineage decisions,
published output/report/lineage/metadata, ignored historical source authority,
and receipt replay with zero upstream reads.

Existing DB11–DB17 behavior remains covered by the same full release-tool
suite. One initial full run encountered the existing DB12 concurrent-cache test
race once; the unchanged test and subsequent full suites passed, so no unrelated
DB12 change was made.

Generated member-index, transformation-lineage, and validation-report documents
all passed the actual DB08 Draft 2020-12 schemas and semantic validators using
the repository-pinned `jsonschema==4.23.0` environment.

## Forest1 acceptance

Workspace parent:

```text
/wc1/utility-watershed-analytics-artifacts/v1/test
```

Sanitized result:

```json
{
  "checks": {
    "exact_member_count": true,
    "geometry_preserved": true,
    "historical_runids_absent": true,
    "receipt_replay_byte_identical": true,
    "runids_preserved": true,
    "source_differences_recorded": true
  },
  "lineage_field_count": 14,
  "matched": 1,
  "source_count": 12,
  "source_unmatched": 1,
  "status": "passed",
  "target_unmatched": 1,
  "temporary_subtree_removed": true
}
```

DB18 temporary-subtree counts were zero before and after acceptance. Existing
test fixtures and the production namespace were untouched.

## Reproducible image

Both final no-cache normalized builds produced:

```text
sha256:cd7db4255485d6767ca6fd02fa52d35735afe564284a359de0dc9d9ef18ae355
```

Image audit result:

```json
{
  "architecture": "amd64",
  "artifact_module_imported": true,
  "enrichment_module_imported": true,
  "image_id": "sha256:cd7db4255485d6767ca6fd02fa52d35735afe564284a359de0dc9d9ef18ae355",
  "input_sha256": "17fecd1342a46ba31ed8069f69f60f42d3ad28ec051831185d833d893576108e",
  "os": "linux",
  "project_files_scanned": 6,
  "rootfs_entries": 6581,
  "source_module_imported": true,
  "status": "passed",
  "unavailable_exit": 20,
  "user": "65532:65532",
  "wrong_digest_exit": 11
}
```

The image contains code only: no NASA descriptor, real or synthetic GeoJSON,
member index, lineage, report, receipt, credential, repository metadata,
server, or client tree.

## Repository gates

Python compilation, Ruff 0.14.1, workflow YAML parsing, changed-document links,
secret/real-source review, executable modes, whitespace checks, and
`git diff --check` passed. DB18 was not committed or pushed, matching package
authority.
