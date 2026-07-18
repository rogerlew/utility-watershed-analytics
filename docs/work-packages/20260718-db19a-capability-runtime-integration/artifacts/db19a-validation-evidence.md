# DB19A validation evidence

Date: 2026-07-18

Host: `forest1`

Starting revision: `3d82885a2546ed689af78a85ac49a8d597be2d26`

Evidence mode: Mixed

No production host, real release, real RHESSys/SBS source, real artifact
coordinate, production database/schema, production `/wc1` namespace,
credential, user account, PII, or external provider was accessed or changed.
All runtime rows and artifact identities were synthetic.

## Runtime and migration proof

```text
python manage.py makemigrations --check --dry-run: No changes detected
focused runtime tests: 13 passed
full server suite: 173 passed
Ruff 0.14.1: passed
```

The focused tests cover exact and logged `EMPTY` RHESSys fallback,
existing-watershed SBS fallback, atomic fallback removal in `ACTIVE`, absent,
disabled, and malformed active rows, direct legacy mode-bypass rejection,
exact active index/config metadata,
no-discovery materialized catalogs, semantic query dispatch, a real in-memory
Parquet column/filter/aggregation read, exact declared output/spatial/SBS tile
URIs, checksum-verified geometry and SBS downloads, and a sanitized capability
summary without artifact configuration.

Migration `watershed.0011_capability_runtime_types` applied successfully in the
fresh test database and model/migration state has no drift.

## Client proof

```text
ESLint: passed with zero warnings
Vitest: 41 files, 587 tests passed
TypeScript + Vite production build: passed, 1,914 modules transformed
```

The client tests additionally prove RHESSys choropleth/time-series requests
contain semantic dimensions only, use the application server endpoint, and
contain no dataset path or SQL authority. Endpoint tests prove SBS downloads
and capability reads remain on the application server rather than constructing
WEPPcloud paths.

Vite retained its pre-existing advisory for chunks over 500 kB; it is not a
DB19A correctness failure. A stale root-owned generated `client/dist` from an
older container was reassigned through a disposable root container before the
clean successful build; no source or serving state was affected.

## Repository gates

Python compilation, focused/full Ruff and Django tests, migration drift,
Prettier, ESLint, focused/full Vitest, TypeScript, production Vite build,
authoritative contract links, secret/scope review, and `git diff --check`
passed. DB19A was not committed or pushed, matching package authority.
