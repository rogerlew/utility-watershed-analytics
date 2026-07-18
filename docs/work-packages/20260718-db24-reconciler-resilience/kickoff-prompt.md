# Kickoff prompt — DB24 reconciler resilience

Execute `package.md` to its honest terminal state from commit `d2d209a` on
`agent/database-backup-deployment-spec`.

Use repository changes, synthetic forward/inverse plans, injected failures,
DB16 recovery, DB20 clean build, and disposable PostGIS on forest1 only. Do not
access `wepp3`, real releases/artifacts/plans, production backup, activation or
rollback, commit, push, open a PR, or dispatch a workflow.

Keep no-op verification read-only, require the exact current target for inverse
rollback, and reuse the existing attempt, staging, writer, and fingerprint
paths rather than adding a second recovery framework.
