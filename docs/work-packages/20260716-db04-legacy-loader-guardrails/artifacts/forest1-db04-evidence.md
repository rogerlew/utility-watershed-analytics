# DB04 `forest1` Guardrail Evidence

Evidence mode: Ran unless marked Static

Executed: 2026-07-17 America/Los_Angeles

Starting revision: `1a1e5e867595d90f447b0e2e812a284755f92025`

## Boundary

DB04 executed only in the repository and isolated development/test containers
on `forest1`. It did not inspect or mutate `wepp3`, dispatch a deployment,
connect a loader to production, delete existing Silk rows, or change any
external service.

## Loader contract

`APP_ENVIRONMENT` accepts only `development`, `test`, or `production`; an
unknown value fails Django configuration and the loader also revalidates the
setting before its first database query.

The exhaustive automated matrix covered all 48 combinations of:

- environment: development, test, production;
- `--force`: absent or present;
- `--dry-run`: absent or present;
- `--all`: absent or present; and
- `--runids`: absent or present.

Every rejected combination was wired to raise an assertion if it reached
`Watershed.objects.count()`, proving rejection before query, transaction, or
deletion. The accepted destructive non-production path is only
`--force --all`; an ordering test proved channels, subcatchments, then
watersheds are deleted before the complete load begins.

Rules proved by the matrix and production-image commands:

- every production `--force` use is rejected;
- `--force --runids` is rejected in every environment;
- bare `--force` is rejected because it would reload only the default subset;
- `--all --runids` is rejected as ambiguous; and
- non-destructive empty-database initial-load and dry-run selections remain
  available.

## Production observability contract

When `APP_ENVIRONMENT=production`, Django excludes:

- the `silk` application;
- `silk.middleware.SilkyMiddleware`; and
- the `/silk/` URL pattern.

Existing Silk database rows are intentionally untouched. Development and test
retain Silk for local diagnostics.

## Executed gates

- Focused DB04 suite: 5 tests passed, including the 48-case matrix.
- Full backend Ruff: passed.
- Full Django suite in the development container: 115 tests passed.
- Production image: `uwa-server-db04-gate:local`, local image ID
  `sha256:3c58c34db4358fe2e8bd3d38cd1c04f632b9e3eea51d17bd1c4837d207643482`.
- Ruff inside the production image: passed.
- Full Django suite inside the production image against its automatically
  created and destroyed isolated test database: 115 tests passed.
- Production-image `--force --all`: rejected before any database connection.
- Development-image `--force --runids selected-run`: rejected before any
  database connection.
- Production Silk app/middleware/URL assertions: passed.
- `compose.prod.yml` render with disposable placeholder values: passed.
- `git diff --check` and documentation link/path review: passed at closeout.

The first production-image test command stopped before test creation because
the calling shell had not loaded the ignored development `.env`; it was rerun
without logging values and passed. A later inline Silk URL assertion had invalid
shell newline escaping; the same assertion was rerun with a single-line URL
pattern check and passed. Neither correction reached production or weakened a
gate.
