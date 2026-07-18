# DB10A forest1 acceptance evidence

Date: 2026-07-17

Host: `forest1`

Root: `/wc1/utility-watershed-analytics-artifacts/v1`

Evidence contains no credentials or source data.

## Storage observation

- filesystem: ZFS mounted at `/wc1`;
- observed capacity: 5,666,391,982,080 bytes;
- observed available: 1,154,988,638,208 bytes;
- observed use: 80%;
- owner: `roger:roger`;
- accepted directory mode: `0700`;
- accepted file mode: `0600`.

The existing `/wc1/utility-watershed-analytics-db-backups` directory remained
separate and unchanged. Its contents were not inspected.

## Acceptance result

```json
{
  "backup": {
    "inventory_sha256": "c7def6aa3bf3c8c83a337cd7eed572a9f33dc12017f844602fed7a57b0f77001",
    "objects": 3,
    "releases": 3
  },
  "negative_proof": {
    "collision_rejected": true,
    "corruption_detected": true,
    "missing_object_detected": true,
    "partial_copy_rejected": true,
    "unavailable_path_rejected": true
  },
  "production_namespace_empty": true,
  "restore": {
    "inventory_sha256": "c7def6aa3bf3c8c83a337cd7eed572a9f33dc12017f844602fed7a57b0f77001",
    "objects": 3,
    "releases": 3
  },
  "status": "passed"
}
```

The restore used a clean temporary directory and was removed after exact hash
comparison. Only the small deterministic fixtures remain under the test
namespace. The production namespace contains no release manifest or object.

## Focused tests

```text
artifact contract validator: passed
artifact contract mutation tests: 10 passed
artifact backup acceptance tests: 4 passed
```
