# DB01 Kickoff Prompt

Execute the governed DB01 package at
`docs/work-packages/20260716-db01-backup-restore-baseline/package.md`.

Work in `/workdir/utility-watershed-analytics` from branch
`agent/database-backup-deployment-spec`, starting at commit
`30a9077d432a5c8582759b614e0ea7224713b685` plus the preserved local Wave 0
authoring changes. Do not push and do not open a pull request.

Read `AGENTS.md`, `docs/ROADMAP.md`,
`docs/database-deployment-architecture.md`,
`docs/database-deployment-roadmap-review.md`,
`docs/wave-0-readiness.md`, and the package before editing.

Authorization is limited to repository mutation and isolated non-production
execution on `forest1`. Do not inspect or mutate `wepp3`, external object-store
accounts, unrelated containers, or shared host services. Preserve existing
uncommitted work and never print or commit secrets.

Deliver the scripts, systemd units, runbooks, tests, and evidence named by the
package. Run every applicable gate, label claims Ran or Static, and terminalize
honestly. If provider acceptance, key ownership, accepted RTO, production-shaped
capacity, or production authority remains unavailable, close with
`EXECUTED-HOLD-OFFHOST-DECISIONS` after completing all safe repository and
isolated development work; do not imply DB01 completion.
