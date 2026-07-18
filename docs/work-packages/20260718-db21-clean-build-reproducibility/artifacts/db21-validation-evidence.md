# DB21 validation evidence

Date: 2026-07-18

Environment: `forest1`, repository
`/workdir/utility-watershed-analytics`, branch
`agent/database-backup-deployment-spec`, starting revision
`8eb707e81907ea41e4e5ffd4e758356cc920e278`.

Evidence mode: Mixed. Commands below are Ran; contract, workflow, scope, and
sanitization reviews are Static. Inputs were generated synthetic files and a
disposable PostGIS database only.

## Production image and server gates

```text
docker build -f server/Dockerfile --target production \
  -t uwa-server:db21 server
```

Result: passed. Final local image ID:

```text
sha256:411101f640ce8fd8d645aad2f02b0ad55ef69d276efecddf2ca0ea181288a4c7
```

This is local evidence for the exact DB21 server tree, not a published release
digest or production authority.

The final image ran against disposable PostGIS on the isolated
`uwa-db21-test` Docker network:

```text
/venv/bin/ruff check --no-cache
/venv/bin/python manage.py makemigrations --check --dry-run
/venv/bin/python manage.py test --verbosity 1
```

Result:

```text
All checks passed!
No changes detected
Found 183 test(s).
Ran 183 tests in 57.803s
OK
```

The focused DB20/DB21 run passed 10 tests in 10.156 seconds. DB21's tests
proved a complete public list/detail/child/capability/removed-run/RHESSys read,
semantic fingerprint sensitivity, fail-before-acceptance behavior for saved
HTML and credential-bearing URLs, geometry rejection with unchanged `EMPTY`,
and sanitized canonical write-once reports. DB20's adjacent negative test
retained exact Parquet-join and late-application rollback proof.

## Independent clean builds

The final image executed
`CleanBuildValidationTests.test_clean_build_acceptance` twice. Each invocation
used a new Django test database and the same generated locked two-run release.
Both passed in independent container processes (`1.630s` and `1.640s`).

`cmp` accepted the complete canonical result bytes. Their SHA-256 was:

```text
4d1ed14089bab309d03378bb3cd8801e8f4a09000d78d57bc1fb5f102356ecd2
```

The sanitized result contained two watersheds, four subcatchments, two
channels, and one capability. Its stable fingerprints were:

```text
domain       84a32b7d1ff276d45ec1bf556e7caa7cdf04bc36cd1313790d4529aafc2134c1
capabilities 216caad062694507a1a696d6046ede7126b97f9c3e6999de2557e875c452269d
```

The fixture's representative public RHESSys choropleth query read an actual
checksum-pinned in-memory Parquet artifact and returned the reviewed values for
both spatial IDs.

## Contract and workflow gates

The DB08 release-schema CLI reported seven schemas, seven valid cases, and
nine expected invalid cases. Its seven unit tests passed. The unchanged DB09
golden/canonical/plan suite passed all 12 tests after the shared canonicalizer
was extracted for server use.

`.github/workflows/server-ci.yml` parsed successfully with PyYAML. Its added
steps create two separate clean-build test lifecycles, compare the entire
canonical output with `cmp`, and print the accepted file SHA-256.

## Boundary review

- `wepp3` was not contacted.
- No real manifest, release, artifact, `/wc1` namespace, production database,
  active pointer, schema, or service was inspected or changed.
- No credentials, `.env` values, source data, dumps, or bulky generated output
  were recorded.
- DB21 was not committed, pushed, published, or dispatched.
- The DB11 code-only `validate` and `build` command boundaries remain
  fail-closed; DB21 is one server-image validation composition over DB20.
