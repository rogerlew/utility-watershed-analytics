# DB30A validation evidence

Date: 2026-07-18 through 2026-07-19

Environment: `forest1` development/backup/artifact host, isolated PostGIS on
`forest1`, and explicitly authorized bounded production work on `wepp3`.

Starting revision: `22647350b9163587485239af1c28e5430937af49` on
`agent/database-backup-deployment-spec`. Production remained at clean fork
`main` revision `5b358c14fffa258f5ec9f1ab55d3645b225888c1`.

Evidence mode: Mixed. This record contains sanitized aggregate results and
credential-free hashes only. Backup contents, database rows, protected
environment values, and bulky artifact bytes remain outside Git.

Terminal status: `EXECUTED-HOLD-PUBLIC-ARTIFACT-SERVING`.

## Backup and restore

- The final pre-mutation encrypted backup completed from `wepp3` to the
  operator-owned `forest1:/wc1` repository as snapshot
  `301088aea8d9378b457478a71c29fe36df7c459cc2f6a04282fbf4e6685cf7ba`.
  The source backup-set SHA-256 was
  `609c9118caee7590432e9b5f3c430e18751b4fd6005568d97fcac4d51880cbf4`.
- An independent `forest1` read found the exact host, scheduled/database tags,
  and source path. Restic checked all 13 snapshots plus rotating data subset
  `1/100` with no errors.
- The exact production database image
  `sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`
  restored into isolated PostGIS. Roles, memberships, extensions, migrations,
  sequences, and table fingerprints matched; schema comparison passed after
  the narrowly bounded equivalent PostgreSQL `CHECK` rendering normalization.

## Reviewed base

- The reviewed identity mapping contains all 126 serving runs exactly once,
  four collection keys, 126 unique watershed keys, and 313 current/historical/
  successor aliases. Its SHA-256 is
  `9e49204f3f83e9c1b44e2608927a6a7627011710bb4c09e9f0794e574acce54b`.
- Capability bootstrap remained limited to Gate Creek, Sooke09, and Sooke15.
  Every locked DB28 index, descriptor receipt, and referenced `/wc1` object
  matched its reviewed size and SHA-256. No Mill Creek or SBS capability was
  inferred.
- Canonical release `2026-07-18.30` exported 126 watersheds, 195,457
  subcatchments, 86,895 channels, and three capability declarations. Manifest
  SHA-256 is
  `bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5`;
  domain fingerprint is
  `dab83d4c098f3b0f6366be8cc2fb8040d9ac670c0919a4f1b2d17c5bf0c78d57`;
  capability fingerprint is
  `4b41b7b2883d67061a1833079fe88cbe3b3fb9d8832999de2e5a812ea02a44d4`.
- The 885 manifest-referenced immutable artifacts total 924,759,445 bytes.
  The manifest and all objects remain private and checksum-addressed below
  `/wc1/utility-watershed-analytics-artifacts/v1/production`.

## Isolated rehearsal

- A source-independent empty rebuild reproduced the exact counts and both
  fingerprints. Database and in-process public-host API validation passed for
  all 126 members and the three materialized capability catalogs.
- The strict DB21 geometry-containment check found a pre-existing Gate Creek
  boundary difference: zero invalid child geometries, but 221 subcatchments and
  one channel are not covered by the legacy watershed polygon. DB30A did not
  rewrite geometry. Exact source/rebuild fingerprints replaced that inapplicable
  clean-source containment assertion for the legacy inverse proof.
- Adoption, rollback to coherent `EMPTY`, all three `legacy-empty` catalog
  fallbacks, and exact retained-ledger re-adoption passed. The final isolated
  state was `ACTIVE` with the reviewed manifest and exact fingerprints.
- Real-scale execution exposed and fixed three tooling defects: canonical
  capability/release fingerprinting now normalizes JSON floats semantically;
  staging state relies on PostgreSQL for bigint constraint enforcement instead
  of overflowing Django's literal constraint query; and an exact rolled-back
  legacy ledger can be re-adopted without discarding immutable history.

## Production execution and rollback

- Production began at coherent `EMPTY`, migration
  `watershed.0011_capability_runtime_types`, 126/195,457/86,895 rows, 126
  provisional identities/aliases, no release ledger, and the unchanged DB05
  container/volume identity. The canonical exclusive operation lock covered
  export, adoption, and verification.
- Reviewed identity assignment preserved all 126 UUIDs and every business-row
  fingerprint while adding successor/history aliases. The independent
  production export reproduced the exact rehearsed manifest and both
  fingerprints. Adoption created one release, 126 run states, 885 lineage rows,
  one attributable attempt, three capability rows, and the active pointer.
- Database counts/fingerprints and all 126 in-process API reads passed. Before/
  after inventories matched for roles, memberships, extensions, migrations,
  and all 57 tables outside the explicit identity/release metadata boundary.
- The required real Gate Creek materialized query then returned HTTP 404:
  `declared RHESSys Parquet is unavailable or invalid`. Independent HTTPS fetch
  proved why: `/artifacts/v1/production/...` returned the 699-byte frontend
  document rather than the requested checksum-addressed object. DB28 and DB30
  explicitly deferred public artifact serving, so DB30A could not repair this
  through an unauthorized Caddy/service deployment.
- The rehearsed exact rollback ran under the exclusive lock. Final production
  is coherent `EMPTY`, release `2026-07-18.30` remains validated history,
  capability rows are zero, reviewed identities and 313 aliases remain, and
  business fingerprints/counts are unchanged. All three catalogs report
  `legacy-empty`; the public Gate Creek fallback query returned HTTP 200 with
  173 rows. The production service, backup timers, clean checkout, exact DB
  container `f315e224...`, exact DB image, and named volume remained healthy.

## Retention and cleanup

- Sanitized external evidence is retained mode `0700` at
  `/wc1/utility-watershed-analytics-db30a-evidence`.
- The encrypted backup snapshot and immutable artifact namespace are retained.
  All disposable restore/rebuild containers, networks, volumes, restored bytes,
  protected temporary environments, transferred production cache, and one-off
  executor image were removed.
- Ruff passed for the full server image and the retained executor. All 212
  Django tests passed with one expected skip against disposable PostGIS. Two
  independent DB21 clean builds produced byte-identical reports with SHA-256
  `8ceb8e94b1ec494c69ba32ef99596bc6ec5ebd6b884b47a7580d36b5b28f2476`.
  Shell syntax, JSON parsing, credential-pattern scan, path review,
  `git diff --check`, and validation-resource cleanup also passed. ShellCheck
  was not installed on `forest1`.
- DB30A must not be marked complete or unlock DB31. The smallest next package
  is DB30B: serve the operator-owned `forest1:/wc1` content-addressed namespace
  at its already-declared public URI, prove exact representative data reads,
  then re-adopt this retained baseline by its existing manifest hash.

## DB30B closure

DB30A's terminal hold above accurately describes its 2026-07-18 execution.
DB30B closed that hold on 2026-07-19: it installed the bounded self-hosted
forest1-to-wepp3 artifact route, verified exact public manifest/TIFF/Parquet
reads and range behavior, and re-adopted the unchanged manifest
`bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5`.
The release is `ACTIVE`, all three reviewed materialized capabilities pass,
and serving-domain rows and fingerprints remain unchanged. DB30A is therefore
closed `EXECUTED-COMPLETE`; DB30B evidence owns the serving implementation and
retry history.
