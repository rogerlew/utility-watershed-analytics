# DB20 validation evidence

Date: 2026-07-18

Environment: `forest1`, repository
`/workdir/utility-watershed-analytics`, branch
`agent/database-backup-deployment-spec`, starting revision
`d778ec3a4fe95aba91fcef3946e4374f70f907a0`.

Evidence mode: Mixed. Commands below are Ran; contract and scope review are
Static. Inputs were generated synthetic files and disposable PostGIS only.

## Production image

```text
docker build -f server/Dockerfile --target production \
  -t uwa-server:db20 server
```

Result: passed. Final local image ID:

```text
sha256:3141d3d992ddc407b7186017f6a911598dfa46aeac8904ef53e17c8336f58317
```

This is local evidence for the exact DB20 server tree, not a published release
digest and not authority to use it in production.

## Focused exact-image gate

The final image ran against a disposable `postgis/postgis:latest` container on
an isolated Docker network with synthetic credentials and database only:

```text
/venv/bin/ruff check --no-cache
/venv/bin/python manage.py makemigrations --check --dry-run
/venv/bin/python manage.py test \
  server.watershed.test_materializer \
  server.watershed.test_staging --verbosity 1
```

Result:

```text
All checks passed!
No changes detected
Found 14 test(s).
Ran 14 tests in 15.753s
OK
```

The four DB20 tests proved:

- exact two-run batch/standalone serving counts and relationships;
- one strict SBS capability with immutable index coordinates;
- both staging and serving maximum batches of one at `batch_size=1`;
- identical canonical row snapshots from two attempts over the same bytes;
- duplicate required Parquet joins fail with no serving/active mutation; and
- late strict capability failure rolls back all serving and pointer changes.

The ten DB16 tests passed unchanged, covering capacity, bounded chunks,
heartbeat, crash residue, lease recovery, retention, cleanup, and serving-state
preservation.

## Full server regression

The exact final production image ran the complete server suite against the same
disposable PostGIS instance:

```text
/venv/bin/ruff check --no-cache
/venv/bin/python manage.py makemigrations --check --dry-run
/venv/bin/python manage.py test --verbosity 1
```

Result:

```text
All checks passed!
No changes detected
Found 177 test(s).
Ran 177 tests in 48.363s
OK
```

## Boundary review

- `wepp3` was not contacted.
- No real manifest, release, artifact, `/wc1` namespace, production database,
  active pointer, schema, or service was inspected or changed.
- No credentials, `.env` values, source data, database dumps, or bulky test
  outputs were recorded.
- DB20 was not committed, pushed, published, or dispatched.
- `data-release build` remains fail-closed in the database-free preparation
  image; the server materializer does not invent DB21 validation or DB22 plan
  inputs.
