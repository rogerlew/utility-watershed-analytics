# DB10 corrected contract evidence

Date: 2026-07-17

Host: `forest1`

Starting correction revision: `245f328ba5e9e1eec05948a08990f9ccf00a5029`

## Authority correction

The operator made `forest1:/wc1` authoritative and rejected a paid provider.
The earlier provider selection was not authorized. No provider account, bucket,
credential, object, support request, purchase, or charge was created.

## Accepted contract

- root: `/wc1/utility-watershed-analytics-artifacts/v1`;
- database backup root remains `/wc1/utility-watershed-analytics-db-backups`;
- owner: `roger`, directories `0700`, files `0600`;
- SHA-256 content keys and verified atomic no-overwrite copies;
- active plus two rollback manifests with no automatic TTL or deletion; and
- clean restore verification plus a 100 GiB free-space floor.

## Validation

```text
{"artifact_classes": 6, "failure_cases": 7, "namespaces": 2, "operators": 1, "status": "passed"}
```

Ten contract mutation tests passed. Live filesystem acceptance is recorded by
the DB10A successor package.
