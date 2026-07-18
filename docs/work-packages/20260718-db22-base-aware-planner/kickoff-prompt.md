# Kickoff prompt — DB22 base-aware planner

Execute `package.md` from published commit `c410628` using repository changes,
synthetic fixtures, and disposable PostGIS on forest1 only. Do not access
`wepp3`, create real release plans, mutate production, commit, push, open a PR,
or dispatch workflows.

Preserve the DB09 plan schemas and canonical digest. Planning must be read-only,
fail on base or compatibility drift, mechanically bind the inverse to the
forward digest, and derive EMPTY-build actions independently.
