# DB30B validation evidence

Status: `EXECUTED-COMPLETE`

Evidence mode: Mixed. This is a sanitized summary; credentials, protected
environment values, raw database rows, immutable artifact bytes, and raw host
output are not committed.

## Reviewed coordinates

- Starting repository revision:
  `d491f0fd46d843be28dce9d146ea0c9e89a4f156`.
- Production host: wepp3; development, backup, and artifact host: forest1.
- Artifact root:
  `/wc1/utility-watershed-analytics-artifacts/v1/production`.
- Public base: `https://firewisewatersheds.org/artifacts/v1/production`.
- Retained release: `2026-07-18.30`.
- Manifest SHA-256:
  `bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5`.
- Adoption-plan SHA-256:
  `994b8c96a0ba54068dba84fa70ec7c0ecadeeb57766f14423ed9c2921855db0b`.
- Persistence-plan SHA-256:
  `5f28be23dbc61adc990889ed5bbe244145d2f14bfee90a6c4d4543e14cc3da52`.

## Self-hosted origin

- The generator found and verified 996 exact manifest-referenced objects: 393
  Parquet, 371 GeoJSON, 129 JSON, and 103 TIFF. The manifest is served as the
  additional exact JSON object and is 469,018 bytes.
- A rootless `roger` user service on forest1 runs Caddy v2.11.2 at reviewed
  image ID
  `sha256:a4ef43ffa2b91c00698ba20caced449418d1e678f50034083882969de8c45f6e`
  and repository digest
  `caddy@sha256:fce4f15aad23222c0ac78a1220adf63bae7b94355d5ea28eee53910624acedfa`.
- The service runs as UID/GID 1000, uses a read-only root filesystem and
  read-only artifact bind, and binds only forest1 Tailscale address
  `100.87.36.38:18080`. Its allowlist contains only wepp3
  `100.74.181.119` and forest1 `100.87.36.38`.
- Negative reachability to forest1 LAN address `192.168.1.108:18080` passed.
  User-service enablement, linger, restart, exact origin reads, and unchanged
  bytes passed.
- Installed generator SHA-256:
  `67614bcc9ab66e0c29b538af0401c8458b02fe24c3250727526a2225d7535533`;
  installed unit-template SHA-256:
  `3d4b2157910fcd0e97304d5645894e7b9109fd13371c1f4d807735d218dd45b8`;
  generated Caddyfile SHA-256:
  `51e6937ae1f00bcefce38e9fb32d8749c35486c0ce693df128e9586456e05717`.

## Backup boundary

- The production backup ran from `2026-07-19T16:36:15Z` and produced source
  archive `pg4django_20260719T163615Z`, 1,216,358,124 bytes, with backup-set
  SHA-256
  `5cb052ae33e3d91f8035143c0a3bc690a26fc9b43a67d681f557a7995d504b4b`.
- Forest1 independently observed encrypted restic snapshot
  `0d970414ff92497f75ba0ad5bc32f41b61482ab3a5fcbfa3da38858b63886afe`
  with host `wepp3` and the expected scheduled/database tags.
- `restic check --read-data-subset=1/100` passed across 14 snapshots with no
  repository errors. No backup provider was used.

## Production route and persistence

- The proxy matches only host `firewisewatersheds.org` and
  `/artifacts/v1/production/*`, strips `/artifacts`, and proxies through
  Tailscale to the forest1 origin. A nested fallback `route` preserves the
  existing API-before-frontend ordering.
- Final repository Caddyfile SHA-256:
  `9c5f4a8aeb24e1f6dffd94d4e210b90b40b1e19bce1513f6056d147b84689831`.
- Protected runtime checksums are: apply helper
  `79505f927b975df3a3172c628aa10245266125759cdb421beb87c640e7ddb0c2`,
  Compose override
  `e07abadc6a127df07dd2bee7759f6aa76d6fa59fffae3ab1e64079b42e82cdcf`,
  ensure helper
  `070a5c7ad7e5d69f7852a1ea0dcc43d2a1d2479caf2145c00e8b477c37031e54`,
  and final systemd drop-in
  `1b6e524d73dfebb255251980b4bb314ef641cdd01f0e54f2452ae95b00eabe45`.
- The root-owned protected Caddyfile and Compose override are mode `0600`; the
  helper directory/scripts are mode `0700`; the systemd drop-in is mode `0644`.
  The Caddyfile mount is exact and read-only.
- `systemd-analyze verify`, canonical `systemctl reload`, and a bounded Caddy-
  only container restart passed. Final Caddy container
  `49ced4ccd618131e948726f1a5d68ce71b6ef6d4474d801cc296fec5685d8507`
  used the retained image and reported zero restarts after verification.

## Adoption, failure, and rollback

- Production began coherent `EMPTY` with one retained validated release, zero
  capabilities, counts 126/195,457/86,895, 126 identities, 313 aliases, and
  unchanged watershed, subcatchment, and channel fingerprints.
- The first executor preflight stopped before database mutation because the
  transferred cache owner UID differed from the executor UID. The bounded
  scripts were corrected to derive the operation UID/GID.
- The first actual adoption passed database and in-process checks, but a real
  Gate Creek POST returned HTTP 405 because the initial Caddy fallback layout
  reordered `try_files` before the API proxy. The adoption script automatically
  executed the exact DB30A rollback. Coherent `EMPTY`, the original Caddyfile,
  and a 173-row legacy Gate Creek fallback were independently verified.
- The corrected nested fallback route passed a functional Caddy rehearsal and
  preserved the API POST. The second exact adoption completed successfully.
  This failure evidence is retained as part of the accepted execution history.

## Final production state

- Active state: `ACTIVE`; active release: `2026-07-18.30`; manifest exact.
- Capability rows: 3. Counts remain 126 watersheds, 195,457 subcatchments, and
  86,895 channels.
- Domain fingerprint:
  `dab83d4c098f3b0f6366be8cc2fb8040d9ac670c0919a4f1b2d17c5bf0c78d57`.
- Capability fingerprint:
  `4b41b7b2883d67061a1833079fe88cbe3b3fb9d8832999de2e5a812ea02a44d4`.
- A real Gate Creek materialized query returned 173 rows. Sooke09 reported 7
  materialized scenarios and Sooke15 reported 5; representative tile reads
  returned valid 856-byte PNGs.
- Roles, memberships, extensions, migrations, data-run states, 885 lineage
  rows, domain tables, staging tables, and unrelated tables were unchanged.
  Expected differences were limited to the active pointer, release
  status/timestamp, one successful attempt, three capability rows, and the
  capability sequence.
- The exact database container remained
  `f315e224ab5704d4610c32cef88544b44073c9dcc38a8de5d2ebc22c8a5cd2d8`
  on volume `utility-watershed-analytics_postgres_data`.

## Independent reads and cleanup

- From forest1, the public manifest matched its exact SHA, JSON media type, and
  469,018-byte size. Representative Parquet digest `c8f207...` matched its
  exact SHA, Parquet media type, and 8,594,298-byte size; representative TIFF
  digest `dd93...` matched its exact SHA, TIFF media type, and 2,098-byte size.
  `Accept-Ranges: bytes` and a 16-byte Parquet `206` request passed.
- Sanitized durable evidence is mode `0700` at
  `/wc1/utility-watershed-analytics-db30b-evidence`. Its 46 files total about
  27 KiB; the `SHA256SUMS` file digest is
  `503b3bf8e29875ffd6740bdb7f12669626052c48a19ce4bf2ff6a1531e0f7b09`.
  A credential-pattern scan passed.
- Disposable transferred cache, operation directory, one-off executor image,
  containers, and temporary configurations were removed. The intended origin,
  proxy persistence files, encrypted backup, immutable artifact namespace, and
  sanitized evidence are retained. Production services/timers are active and
  the production checkout remains clean on fork `main`.

## Repository validation

- All three generator unit tests passed with Python 3.12.
- Ruff passed for the generator and its test in the retained DB30A image.
- Shell syntax passed for the apply, ensure, adoption, and rollback scripts;
  ShellCheck was not installed on forest1.
- Both reviewed JSON plans parsed, the merged production Compose render kept
  the exact protected Caddyfile bind read-only, the Caddy configuration
  validated, and the origin user unit passed `systemd-analyze --user verify`.
- Documented repository paths, a credential-pattern scan, and
  `git diff --check` passed. No full Django suite was needed because DB30B does
  not change application code; the live API/capability checks exercised the
  affected behavior.
