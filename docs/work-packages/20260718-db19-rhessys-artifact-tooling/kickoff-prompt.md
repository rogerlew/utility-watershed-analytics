# DB19 kickoff prompt

Execute DB19 from revision
`0b75d58c3796495fe03334765b418b625705b6e6` on branch
`agent/database-backup-deployment-spec` in
`/workdir/utility-watershed-analytics` on `forest1`.

Implement one closed RHESSys preparation path for dynamic Parquet/spatial-input
and precomputed GeoTIFF modes. Pin every source by URL, SHA-256, byte count, and
geometry revision; validate exact scenarios, variables, physical schemas, CRS,
bounds, dimensions, bands, nodata, and representative reads; publish and
re-fetch through the DB12 local client; emit a DB08 capability index and exact
replay receipt; and prove explicit capability removal as reviewed set
difference.

Use only synthetic fixtures and a disposable subtree below
`/wc1/utility-watershed-analytics-artifacts/v1/test`. Remove it after proof.
Do not inspect real RHESSys sources, access `wepp3`, publish a real release,
change runtime discovery, activate capability state, commit, push, or open a
pull request. Do not select or provision any storage provider: `/wc1` is the
binding artifact store.
