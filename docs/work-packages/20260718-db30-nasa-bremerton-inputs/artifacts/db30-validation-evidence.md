# DB30 validation evidence

Date: 2026-07-18

Environment: `forest1`, bounded read-only source access to the two DB30 batch
trees on `wepp1`, the public checksum-pinned NASA enrichment source, and the
operator-owned artifact namespace below `/wc1`.

Starting revision: `a5a0616542c3258a6a17e2da3c4b63548cb07083` on
`agent/database-backup-deployment-spec`.

Evidence mode: Mixed. This record contains sanitized aggregate results,
checksums, and credential-free coordinates only. Tokens, source trees, and
bulky artifact bytes remain outside Git.

## Accepted membership

- NASA successor: 93 explicit members in source feature order. Every stable key
  is unique; each member retains the current old-batch and historical source
  run IDs as aliases while its current run ID uses
  `batch;;nasa-roses-202606-psbs;;`.
- Bremerton: `Bremerton01`, `Bremerton02`, and `Bremerton03` only, with stable
  keys `bremerton-01` through `bremerton-03`.
- Bremerton04: explicitly excluded by the operator after all five required
  child products were confirmed absent. The source feature remains represented
  in the locked raw master and exact descriptor exclusion list.

## Published inputs

| Input | Members | Sources | Source bytes | Index SHA-256 | Receipt SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| NASA successor | 93 | 467 | 330,826,629 | `216dcd73528f2f2498b36b1f9b9108ad55e724915318c2e8b25add935bbb74fe` | `1f129dc19402f5b3b76bc83732ce09e13ef04e9aaa5af46c39bd650f0ff6e3d3` |
| Bremerton approved set | 3 | 16 | 1,235,895 | `5e16352738f9576ad9c54359f8d89fff57c73ff0cc7ea43241e82998bd91b16f` | `5958c38579dd2be73726e7883363c1a39c10bd8578401a7889220b3a6e9378c8` |

Both receipts replayed from new empty caches with the upstream fetcher hard-
failed. Each made zero upstream calls and reproduced its exact index and
receipt bytes.

## NASA enrichment

- The public enrichment input remained exactly 8,935,440 bytes with SHA-256
  `be152890a8436d931f962b6eabe32287935d8da5303c5f532985ec835e8954ce`.
- The real join matched all 93 targets, left zero targets unmatched, recorded
  302 source-only features, and found zero duplicate join keys.
- All 93 historical source run IDs were ignored. Feature count, order, current
  run IDs, `WWS_Code`, and geometry were preserved exactly; source and target
  geometries matched for the 93 joined features.
- The normalized target and enriched output are intentionally idempotent at
  SHA-256 `75e65ee13bc756634b25af4f806cf927c67a5a84e3973593e88c3c54551e2bb0`.
  Lineage `951b14e9a6133fc864b134e5b353a0fe58691615aa2fd08b63c1984a168be5e0`
  and validation report
  `ef91ab531dda5a388cdacfd664a98e275f8692b693857ea8186fd57d1b500aa6`
  record the full proof.

## Counts and joins

| Input | Raw subcatchment features | Materialized subcatchments | Raw channel features | Materialized channels | Exact Parquet joins |
| --- | ---: | ---: | ---: | ---: | ---: |
| NASA successor | 168,265 | 101,481 | 270,118 | 42,523 | 279 |
| Bremerton approved set | 495 | 321 | 961 | 135 | 9 |

Raw GeoJSON uses multipart records. DB30 groups subcatchments by `TopazID`
with agreeing `WeppID`, and channels by `(TopazID, WeppID, Order)`. Every group
produced one valid DB20 multipolygon and every hillslope, soil, and land-use
Parquet had a non-null unique Topaz set exactly equal to its materialized
subcatchment set.

## Negative, storage, and tests

- Real/source-shaped negative checks rejected missing, extra, duplicate,
  unlisted, and receipt-coordinate-drift membership before acceptance.
- The complete retained production namespace contains 1,047 objects totaling
  4,343,444,249 bytes. Independent full reads produced inventory SHA-256
  `e58f128ea588b8a81c0f42bacd447a1b92da5944ab5d49a1ef8d1ff0d9b8ebf0`;
  every object matched its digest path and owner/mode requirements.
- All 66 release-tool tests, all seven DB08 schemas with nine
  negative fixtures, and DB09 fingerprints/plans passed. Focused materializer
  tests and all 209 Django tests passed with one expected skip.
- Production images built successfully as
  `sha256:e24dd00deac7d07da957f03289ac44dfa2b7bdc0ce30d706f3d20589b342cf3e`
  for the release tool and
  `sha256:e38c037f5899c9eb29005903ae9f955d71ea802634f46992c22cb925f06c7e12`
  for the server.

No `wepp3` access, database mutation, activation/adoption, public-serving
change, provider selection, deletion, workflow dispatch, commit, push, or PR
action occurred.
