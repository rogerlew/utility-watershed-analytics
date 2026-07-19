# DB29 validation evidence

Date: 2026-07-18

Environment: `forest1`, public WEPPcloud/API reads, and the authorized local
artifact namespace under `/wc1`.

Starting revision: `0b7021c` on
`agent/database-backup-deployment-spec`.

Evidence mode: Mixed. Credentials and bulky source/artifact bytes remain
outside Git.

## Results

DB29 stopped on the defined `EXECUTED-HOLD-RHESSYS-SOURCE` boundary. The
successor ordinary inputs are accepted and retained; the required non-empty
precomputed capability is unavailable from every authorized source checked.
No `wepp3`, database, activation, serving, provider, delete, workflow, commit,
or push action occurred.

### Successor ordinary inputs

- Exact public project: `some-oligopoly/disturbed9002_wbt`.
- Stable collection/watershed key: `mill-creek`; successor run ID:
  `some-oligopoly`; former `mdobre-invincible-scarab` retained only as alias.
- Six sources total 5,194,784 bytes. Member index SHA-256:
  `be3cdd7bd1f517ae410c8622eec15d7b34b7371cba78b05b79835cdc416a189d`.
  Receipt SHA-256:
  `6c062a3151ad6dcc3190f5b8abc525a50fe8283bbf2492920c190129759296d1`.
- The index contains one watershed, 2,286 subcatchment features, 1,718 unique
  subcatchment `TopazID` values, and 4,245 channels. Hillslope, soil, and
  land-use Parquets each have a unique non-null ID set exactly equal to the
  GeoJSON set; required channel relationship fields are present.
- Receipt replay used a clean cache with the upstream fetcher made fatal. It
  performed zero upstream calls and reproduced exact index and receipt bytes.

### Durable storage

- Nine referenced objects totaling 5,199,550 bytes independently matched their
  content-addressed paths, owner `roger`, and file mode `0600` below private
  directories. The whole production namespace now contains 372 objects and
  4,007,689,465 bytes.
- About 1.1 TiB remained free. No partial, staging, or disposable cache files
  remained. Accepted ordinary objects remain under the production no-delete,
  no-TTL retention contract.

### RHESSys source hold

- The successor's public root listing contains no `rhessys/` directory and its
  `browse/rhessys/maps/` coordinate returns 404.
- All 56 coordinates in the deployed seven-scenario/eight-variable registered
  matrix returned 404 under the confirmed successor project.
- The exact expected path checklist is retained in
  `artifacts/mill-creek-rhessys-expected-files.txt`; it is labeled as registry
  expectation rather than observed inventory.
- The public successor catalog returned 82-byte JSON with SHA-256
  `b753b993dcb1668489ce38244dfa66fa4a2779b4a692bdf34d46411fbc23e620`
  and `capability.available: false` with empty scenarios and variables.
- A bounded `/wc1` search found no successor, former-run, or Mill Creek RHESSys
  map tree. The former direct coordinate returned HTTP 401; no credential was
  used, printed, or persisted, and the former run is prohibited as authority.
- Consequently no RHESSys descriptor/index/receipt was authored and no empty,
  partial, or inferred capability was published.

### Verification and next action

The full 61-test release-tool suite, seven valid/nine invalid DB08 fixtures,
DB09 fingerprints/plans, actual member-index schema/semantic validation,
JSON parsing, secret scan, and `git diff --check` passed.

To resume, place or regenerate the complete reviewed Mill Creek
`rhessys/maps/<scenario>/<variable>.tif` tree under `some-oligopoly` or an
operator-owned `/wc1` source path. DB29 can then close the exact matrix, publish
it beside the retained ordinary inputs, replay from receipts, and only then
author application-reference changes. No paid provider is required.
