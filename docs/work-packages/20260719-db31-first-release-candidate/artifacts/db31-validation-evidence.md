# DB31 validation evidence

Status: `EXECUTED-COMPLETE`

Evidence mode: Mixed

## Candidate coordinates

- Release: `2026-07-19.31`
- Target manifest SHA-256:
  `21d8b279d627f4000ca9d2826ec591e07bd611839c88177eb079a39d395988ec`
- Target domain fingerprint:
  `212ca78aa2fff24a75e4ea952b27087dcdc7e6b360010018474581af27d7d386`
- Target capability fingerprint:
  `4b41b7b2883d67061a1833079fe88cbe3b3fb9d8832999de2e5a812ea02a44d4`
- Source-validation report SHA-256:
  `a3463d0be077dace0a8572785b9dfcff645cce9feb45f1af3fb0b6793528deca`
- Target-canonicalization map SHA-256:
  `7e83834dc425c76dbef9698816fe455a4dfe86b8496469ef489d1d12365822d3`

The target contains 129 watersheds, 110,270 subcatchments, 46,296 channels,
and three RHESSYS capabilities. Membership is Gate Creek, all 31 reviewed
Victoria members, Mill Creek run `some-oligopoly`, all 93 NASA successor
members, and Bremerton01–03. Bremerton04 and Mill Creek RHESSYS are absent.

## Deterministic target preparation

Every accepted DB28–DB30 source reference was verified locally by exact path,
size, media type, and SHA-256 with zero upstream fetches. The pinned DB20
materializer exposed two source-shape facts that DB28–DB30 source locking did
not test:

- 346 of 387 Parquet artifacts had unique, non-null Topaz identities but
  unordered physical rows. PyArrow 22.0.0 produced immutable ascending-Topaz
  target copies while retaining every source and target hash.
- All 129 accepted source boundaries fail strict containment of their accepted
  child geometries; several NASA source bounds materially disagree with child
  extents. GEOS 3.13.1 derived each target boundary as the child-geometry
  convex hull with a fixed `1e-9` degree robustness buffer. All derived
  boundaries are valid, cover every child, and have subcatchment-area ratios
  from 0.528 to 0.906.

The immutable mapping records 346 Parquet and 129 boundary transformations.
No accepted source object was overwritten or deleted.

## Clean builds

Two independent empty PostGIS 17.5/PostGIS 3.5.2 databases used separate
containers, volumes, networks, protected disposable credentials, and the
retained `uwa-server:db30a` executor. Both reports passed exact artifact,
staging, geometry, database, application, and capability checks:

| Build | Report SHA-256 | Result |
| --- | --- | --- |
| 1 | `60f8a5d14f7392de23e0b8504b4ab36eaa2a849c026091eda1b8a2ea46297fc3` | Exact target fingerprints/counts; passed |
| 2 | `57c25880ec39c0b9b8723690b0a8248d74e01ba7d6ebcf5a745267e8c02fffec` | Exact target fingerprints/counts; passed |

Both builds returned 173 representative Gate dynamic rows, materialized Gate
and Sooke capability catalogs, valid Sooke09/Sooke15 tiles, no Mill Creek
RHESSYS capability, 94 absent former run IDs, and no Bremerton04. The reports'
semantic outcomes are identical; report bytes differ only in build identity
and execution timestamps. Two NumPy masked-array cast warnings occurred during
real RHESSYS reads without changing the successful response checks.

## Bound plans

The planner independently rebuilt and fingerprinted the exact adopted DB30A
base manifest `bb9729bc...ea5` at domain fingerprint `dab83d4c...8d57` before
writing plans. All plans pass DB09 schemas and semantic/inverse checks.

| Plan | SHA-256 | Result |
| --- | --- | --- |
| Forward | `086051b784a1de8b50db8402d2dd9d948501632f66741c721d7641ec519c722d` | 3 adds, 126 changes, 0 removals |
| Exact inverse | `a57dad600f09a9dc139614c2bcb500e5d0e8ee1702dae17f971a0ca1197c1112` | Mechanically bound to canonical forward bytes |
| EMPTY build | `822828e7f95a60c3d0608047215acbeb7a70a841c4f354dc635812c08a130974` | Independently keyed; used by both builds |

Expected row deltas from the adopted base are +3 watersheds, -85,187
subcatchments, and -40,599 channels.

## Validation and cleanup

- DB08 manifest/report and DB09 plan schema/semantic checks passed against the
  exact retained files.
- Nineteen focused release-schema and fingerprint-plan tests passed.
- The pinned server image passed all 212 Django tests in isolated PostGIS;
  one existing test was skipped.
- Ruff passed for `server/` and the DB31 operations harness. A broader
  repository Ruff command also reported the pre-existing unused `sys` import
  in `scripts/tests/test_database_deployment_orchestrator.py`; DB31 did not
  alter that file.
- `git diff --check`, focused secret-pattern review, immutable publication,
  and final Docker/container/volume/network cleanup passed.
- No `wepp3`, production database, provider, workflow, commit, push, or pull
  request action occurred.
