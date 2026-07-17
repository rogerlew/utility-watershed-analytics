# DB06 `wepp3` Domain Identity Evidence

Date: 2026-07-17

Evidence mode: Ran

## Authority and execution

The user authorized the aggregate-only DB06 identity audit on production host
`wepp3` and publication of sanitized results. The audit ran under the shared
operations lock against the existing serving database. It selected counts,
constraint metadata, duplicate-group counts, orphan counts, field signatures,
and migration names inside an explicit read-only transaction. It selected no
row values and made no database, container, image, service, or checkout change.

The running application image predates the DB06 management command. Rather than
build or deploy an image, the exact reviewed `identity_audit.py` source at
SHA-256 `f80fbcae8e23f995f5760297a1e91fe4f458c8b338da7492d205f03a0712335a`
was streamed over stdin to `python manage.py shell` in the existing server
container. A small in-memory wrapper serialized the same report and returned a
non-zero exit on violations. The container filesystem remained unchanged.

## Sanitized result

| Domain table | Rows | Duplicate business-key groups | Duplicate rows | Orphans | Business key constrained |
| --- | ---: | ---: | ---: | ---: | --- |
| Watershed | 126 | 0 | 0 | Not applicable | Yes (`runid` primary key) |
| Subcatchment | 195,457 | 0 | 0 | 0 | No |
| Channel | 86,895 | 0 | 0 | 0 | No |

- Audit contract version: 1.
- Read-only transaction: true.
- Status: passed.
- Violations: 0.
- Applied watershed migrations: 6.
- Warnings: subcatchment and channel business keys are not enforced by database
  constraints.
- Raw aggregate report: 15,640 bytes; SHA-256
  `07c10564ba09c1cc084c2abd7b1e4bd17dca86164fc375c66eb889125e7e21d3`.

The report schema was allowlisted and scanned for password, secret, token, and
credential terms. It contained no row-payload keys or credential values. The
temporary mode-`0600` raw report was deleted after this summary was validated.

## Post-check

Database container `f315e224...` remained healthy with zero restarts on
`utility-watershed-analytics_postgres_data`. Server container `f4085f6d...`
remained running with zero restarts. The production checkout remained clean;
the streamed audit files remained absent from the container filesystem; and
the two canonical roots plus their API schema routes returned HTTP 200.

This evidence establishes that the accepted current production dataset has no
duplicate groups for the audited business keys and no child orphans. It does
not turn those observations into database constraints; DB07 must decide the
future stable identity contract before a later migration adds enforcement.
