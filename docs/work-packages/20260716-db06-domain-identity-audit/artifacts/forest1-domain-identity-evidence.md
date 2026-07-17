# DB06 `forest1` domain identity evidence

Date: 2026-07-16

Host: `forest1`

Starting revision:
`5931ca1058881a532678e053794f1509e4d40434`

Evidence mode: Mixed

Production access during this evidence run: none

## Environment

- Docker Engine 29.4.2
- Docker Compose v5.1.3
- production test image:
  `sha256:4ef239173320f1a59edc2d37e62f0ceda5821af106377efe0df50a010e294250`
- Python 3.12.13
- Django 5.1.4
- Ruff 0.14.1
- development database: PostgreSQL 17.5, queried inside an explicit read-only
  transaction

## Static domain and consumer review

Reviewed:

- `server/server/watershed/models.py` and migrations `0001`–`0006`;
- loader configuration, discovery, orchestration, writer field maps, geometry
  grouping, and Parquet joins under `server/server/watershed/loaders/`;
- watershed, child, SBS, RHESSys spatial, and RHESSys output routes/views;
- GeoJSON ID construction and explicit API property schemas;
- client route parameter, endpoint construction, React Query keys, map/search
  selection, land-use, RAP, scenario, SBS, and RHESSys consumers; and
- PostgreSQL constraints and the architecture's current key assumptions.

Durable results are in `docs/database-domain-identity-audit.md`. The review
identified three watershed-domain tables, ten persistent Django state tables,
five Silk observability tables, and 37 PostGIS/TIGER/topology infrastructure
tables. It also identified current `runid` compatibility coupling, volatile
child GeoJSON feature IDs, missing child unique constraints, Topaz-only Parquet
joins, and API/client schema-description drift.

## Development catalog query

An aggregate `psql` script ran with `BEGIN TRANSACTION READ ONLY` and rolled
back. It listed all 55 non-system tables, exact counts, constraints, duplicate
business-key groups, and transaction mode.

Key results:

- transaction read-only: `on`;
- watershed, subcatchment, and channel rows: 0 each;
- subcatchment duplicate `(watershed_id, topazid)` groups: 0;
- channel duplicate `(watershed_id, topazid, weppid, order)` groups: 0;
- watershed `runid` primary key: enforced;
- child-to-watershed foreign keys: enforced and Django cascade-deleting;
- child business-key unique constraints: absent;
- non-domain foreign keys into watershed-domain tables: absent;
- `auth_user`: 1 development operational account; and
- no row values or credential values were selected or preserved.

The zero duplicate result is not accepted production evidence because all three
domain tables are empty.

## Executable audit proof

Command:

```bash
docker compose exec -T server \
  python manage.py audit_domain_identity --fail-on-violations
```

Result: passed. The report declared a read-only transaction, zero violations,
zero domain rows, no duplicate groups, and no orphans. It warned that both child
business keys lack database constraints and that empty tables cannot establish
dirty-data absence. A scan of the JSON found no password, secret, token, or test
row identity.

Targeted gate:

```bash
docker compose exec -T server ruff check --no-cache \
  server/watershed/identity_audit.py \
  server/watershed/management/commands/audit_domain_identity.py \
  server/watershed/test_identity_audit.py
docker compose exec -T server python manage.py test \
  server.watershed.test_identity_audit --verbosity 2
```

Result: Ruff passed; 4 tests passed. Tests prove deterministic aggregate-only
output, current constraint/cascade reporting, duplicate subcatchment/channel
detection, non-zero failure mode, and absence of DDL/data-mutation statements.

## Full backend gates

Commands:

```bash
docker compose exec -T server python manage.py check
docker compose exec -T server python manage.py makemigrations --check --dry-run
docker compose exec -T server python manage.py test --verbosity 1
docker build -f server/Dockerfile --target production \
  -t utility-watershed-analytics-server:db06 server
docker run --rm utility-watershed-analytics-server:db06 \
  ruff check --no-cache
```

Results:

- Django system check: passed;
- migration drift: none;
- complete Django suite: 110 tests passed;
- production server image: built; and
- full production-image Ruff check: passed.

## Original skipped and held evidence

- Production aggregate audit: not run; no production read-only authority.
- Non-empty local source audit: not run; expired development tokens left the
  current domain empty and no large external source data was fetched.
- Client gates: not run; client behavior did not change and source was reviewed
  only as a compatibility consumer.
- Production uniqueness claim from the earlier architecture draft: not accepted;
  DB06 found no linked preserved command or report.

At this stage DB06 correctly terminated on
`EXECUTED-HOLD-PRODUCTION-EVIDENCE` rather than claiming production counts,
uniqueness, or dirty-data absence. The later separately authorized aggregate
production audit resolved that hold; its sanitized result is in
[`wepp3-production-domain-identity-evidence.md`](wepp3-production-domain-identity-evidence.md).
