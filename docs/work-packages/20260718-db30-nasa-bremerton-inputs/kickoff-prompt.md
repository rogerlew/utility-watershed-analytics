# Kickoff prompt — DB30 NASA successor and Bremerton locked inputs

Execute `docs/work-packages/20260718-db30-nasa-bremerton-inputs/package.md`
from `forest1` at starting revision `a5a0616`.

Read only the two DB30 batch trees below `wepp1:/geodata/wc1/batch`. Bind each
source feature through BatchRunner's persisted validated member template to an
explicit reviewed current run ID; do not copy NASA's historical source run IDs
or invent Bremerton run IDs. The operator's execution-time decision explicitly
excludes Bremerton04 because it has no required child products. Publish the six
ordinary roles for all 96 approved members
and the DB18 NASA enrichment outputs immutably below the operator-owned
`forest1:/wc1/utility-watershed-analytics-artifacts/v1/production` namespace.

Stop on identity, geometry, membership, source, checksum, format, join,
enrichment, capacity, permission, replay, or validation drift. Do not access
`wepp3`, mutate source data or a database, activate/adopt a release, change
public serving, select a provider, delete anything, dispatch a workflow,
commit/push DB30, or open a PR.
