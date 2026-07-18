# DB19 validation evidence

Date: 2026-07-18

Host: `forest1`

Starting revision: `0b75d58c3796495fe03334765b418b625705b6e6`

Evidence mode: Mixed

No real RHESSys source coordinate, real inventory descriptor, production host,
production namespace, credential, user data, or PII was accessed. All source
bytes and identities were synthetic.

## Focused and regression tests

```text
release-tool CLI, artifact, source, enrichment, and RHESSys tests: 58 passed
acceptance and image-verifier wrapper tests: 11 passed
```

Ten DB19 tests cover bounded Parquet footer schema and representative data-byte
reads, GeoTIFF metadata and strip reads, corrupt envelopes/IFDs/sample ranges,
dynamic/precomputed/combined modes, missing and partial scenarios, renamed
variables, geometry revision mismatch, physical Parquet type drift, CRS
mismatch, interrupted publication cleanup, immutable publication/re-fetch,
explicit capability removal, and zero-upstream exact replay. CLI routing and
output-file behavior are covered separately in the full release-tool suite.

The generated RHESSys index passed the actual DB08 Draft 2020-12 schema and
semantic validator using the repository-pinned `jsonschema==4.23.0`
environment. The complete data contract passed seven positive schemas and nine
negative fixtures. DB09 validation passed five fingerprint subjects, four plan
schemas, three plans, five semantic mutations, and twelve unit tests after
scenario/column normalization and golden-hash reconciliation.

## Forest1 acceptance

Workspace parent:

```text
/wc1/utility-watershed-analytics-artifacts/v1/test
```

Sanitized result:

```json
{
  "checks": {
    "all_sources_content_addressed": true,
    "exact_scenario_coverage": true,
    "geometry_revision_locked": true,
    "receipt_replay_byte_identical": true,
    "representative_assets_refetched": true
  },
  "mode": "both",
  "removed_capabilities": ["example-north"],
  "scenario_count": 2,
  "source_count": 4,
  "status": "passed",
  "temporary_subtree_removed": true
}
```

The sorted top-level namespace fingerprint was identical before and after the
acceptance run. Existing test fixtures and the production namespace were not
modified.

## Reproducible image

Both final no-cache normalized builds produced:

```text
sha256:14fd35b2cbfeac308cd796e466af1acf59c29f5e70ddea72cfa950a057217b42
```

Image audit result:

```json
{
  "architecture": "amd64",
  "artifact_module_imported": true,
  "enrichment_module_imported": true,
  "image_id": "sha256:14fd35b2cbfeac308cd796e466af1acf59c29f5e70ddea72cfa950a057217b42",
  "input_sha256": "17fecd1342a46ba31ed8069f69f60f42d3ad28ec051831185d833d893576108e",
  "os": "linux",
  "project_files_scanned": 7,
  "rhessys_module_imported": true,
  "rootfs_entries": 6582,
  "source_module_imported": true,
  "status": "passed",
  "unavailable_exit": 20,
  "user": "65532:65532",
  "wrong_digest_exit": 11
}
```

The image contains code only: no descriptor, Parquet, GeoTIFF, capability
index, receipt, credential, repository metadata, server, or client tree.

## Repository gates

Python compilation, Ruff 0.14.1, workflow YAML parsing, executable mode,
changed-document review, schema links, secret/scope review, whitespace, and
`git diff --check` passed. DB19 was not committed or pushed, matching package
authority.
