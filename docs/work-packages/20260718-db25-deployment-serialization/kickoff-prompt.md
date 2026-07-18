# Kickoff prompt — DB25 deployment serialization

Execute `package.md` to its honest terminal state from commit `92ce360` on
`agent/database-backup-deployment-spec`.

Use repository/static workflow checks, synthetic releases and plans,
disposable credential files, and disposable PostGIS on forest1 only. Do not
access `wepp3`, production credentials or roles, run production migrations,
dispatch a production workflow, use real release inputs, commit, push, open a
PR, or mutate external systems.

Reuse DB03's lock and existing compatibility/reconciler contracts. Keep DB26's
orchestrator and DB27's final protected release workflow out of scope.
