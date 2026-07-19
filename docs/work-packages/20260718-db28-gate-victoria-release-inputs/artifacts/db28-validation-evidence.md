# DB28 validation evidence

Date: 2026-07-18

Environment: `forest1`, public WEPPcloud source reads, and the authorized local
artifact namespace under `/wc1`.

Starting revision: `9512d05` on
`agent/database-backup-deployment-spec`.

Evidence mode: Mixed. This record contains sanitized aggregate results,
checksums, and public coordinates only. Credentials and bulky source/artifact
bytes remain outside Git.

## Results

DB28 completed without accessing `wepp3`, changing a database, activating a
release, configuring public artifact serving, selecting a provider, or deleting
source or artifact data.

### Membership and source lock

- The authoritative public inventory response was 1,609,932 bytes with SHA-256
  `2e5a58909a0c3e75b6c64681939f49e9c52ac1e3f1c831266faa762042504017`.
- Victoria locks 31 explicitly mapped members: `Council`, `Deception`,
  `Goldstream`, `Leech`, `Sooke01`–`Sooke04`, and `Sooke06`–`Sooke28`.
  Local-only `Sooke05` is excluded rather than inferred into the release.
- Gate Creek locks one ordinary member at public run `aversive-forestry`.
  Its WGS84 boundary was selected after the projected boundary failed the
  ordinary-source coordinate gate.

### Published indexes and receipts

| Input | Sources | Source bytes | Index SHA-256 | Receipt SHA-256 |
| --- | ---: | ---: | --- | --- |
| Gate ordinary | 6 | 5,776,403 | `45f8316b9efc43d92effe6a74ac60851d06b19a881b8d6c25ba328443b073aef` | `82027b69b5dcae3334b851eb08c38be22e29212e5ced5b7b200a260f356f9f82` |
| Victoria ordinary | 156 | 14,976,234 | `fa34c9c77c1be89a0b557027dffe064883df7c0579fea72ad911f009a1911a37` | `18b2cd228ce0a46434201eb4977e5207eb27cad6c0f80f047d327eef513a4da4` |
| Gate RHESSys | 53 | 3,981,156,759 | `bc3786dfd122e1a2de7d2fd824633778b6f4950413d4cb222e79fbc51cf56a87` | `b19fb4aac80ed0bf9e5b820bc1214e3e473f19d0a82867ffced755e0d3365dfb` |
| Sooke09 RHESSys | 56 | 205,016 | `c33cb45dbfea306b36549e67392c377b2de9d79804736b7fc449ce082fa8e901` | `bf125cf933ca6e3be25083631c05f4b192ba3a52bbadc146358e9e15af060018` |
| Sooke15 RHESSys | 40 | 270,157 | `3bb92194b2c5664c762624f0d3ac09a6550c3b43dbe41efc40df10c1157fdb0e` | `68f7be93a390d90cb0505f93f8aad3aae8515b72454d85140b947927b85a7cd5` |

### Structural and semantic proof

- Draft 2020-12 schema, safe-content, and cross-file semantic validation passed
  for both ordinary member indexes and all three RHESSys indexes.
- Gate ordinary contains 3,696 subcatchment features and 4,598 channels;
  Victoria contains 8,207 subcatchment features and 10,123 channels. All 96
  hillslope/soil/land-use Parquet-to-GeoJSON unique `TopazID` set joins passed.
- Gate RHESSys locks 32 spatial rasters, 18 Parquets across `S1`, `S2`, and
  `S4b`, and three geometry assets. Every Parquet query coordinate produced a
  real row read. Hillslope and patch identity sets exactly matched their
  scenario geometry sets. The S2 geometry has 12,132 features and 12,130 unique
  IDs because IDs `31460` and `34408` each have two geometry features.
- Daily Parquets physically span 1980–2024 and expose the reviewed 1985–2024
  query interval. Yearly patch Parquets physically span 1980–2023 and expose
  1985–2023; an initial 2024 declaration was corrected before acceptance.
- All 32 Gate rasters opened and returned a representative pixel. Dimensions,
  bounds, CRS, and bands matched. Four legacy rasters expose `-32768` through
  the DB19 TIFF tag parser but not through GDAL's nodata API; this bounded fact
  is recorded rather than hidden. All 56 Sooke09 and 40 Sooke15 maps matched
  their declared metadata and returned a representative pixel.
- S4b patch data uses the 44,203-ID 1985 geometry. Deep join validation caught
  and corrected an initial association with S2's 12,130-ID 2021 geometry.

### Replay, storage, and build proof

- Each accepted descriptor replayed from its receipt with the upstream fetcher
  hard-failed. All five replays made zero upstream calls and reproduced exact
  index and receipt bytes.
- An independent full read hashed every content-addressed object. The namespace
  contains 363 objects totaling 4,002,489,915 bytes with inventory SHA-256
  `da89a5dcc3406d1f677bdb82f777d26c631c38a11db81b78901a5ada0253a71c`.
  Every object hash matched its path; all files are owner `roger`, mode `0600`,
  below owner-`roger` mode-`0700` directories. Four superseded generated
  index/receipt objects remain harmlessly retained because DB28 had no delete
  authority.
- `/wc1` retained about 1.1 TiB free. No staging or partial files remained.
- The full 61-test release-tool suite passed, including the 23 focused
  source/RHESSys tests. Seven valid and nine invalid schema fixtures plus the
  DB09 fingerprint/plan contract passed. Two no-cache normalized image builds
  produced the same audited image ID
  `sha256:fa7ed8fe30f5faa9535ad6f41c728bebc8c091b39139fd3fe29b3feeaa133ced`.

### Honest retries

The first upstream Victoria master request returned HTTP 401, so no credential
was printed or persisted; the reviewed public inventory plus the existing local
source tree was used instead. Pre-acceptance retries also exposed a projected
Gate boundary, legacy TIFF extension tags, a transform-only TIFF, physical
Parquet leaf names outside the synthetic test assumptions, the yearly range
overstatement, and the S4b geometry association. Each issue stopped acceptance,
was fixed in the smallest applicable contract/tool boundary, and was rerun.
The final accepted indexes are the hashes above.
