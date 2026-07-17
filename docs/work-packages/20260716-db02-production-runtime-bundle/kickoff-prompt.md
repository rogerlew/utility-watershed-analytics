# DB02 Kickoff Prompt

Execute the governed DB02 package at
`docs/work-packages/20260716-db02-production-runtime-bundle/package.md` in
`/workdir/utility-watershed-analytics` on branch
`agent/database-backup-deployment-spec`. Preserve every existing local change.
Do not push and do not open a pull request.

Read `AGENTS.md`, `docs/ROADMAP.md`,
`docs/database-deployment-architecture.md`,
`docs/database-deployment-roadmap-review.md`,
`docs/wave-0-readiness.md`, DB01's terminal package, and DB02 before editing.

Authorization is limited to repository mutation and disposable non-production
fixtures on `forest1`. Do not inspect or mutate `wepp3`; do not infer its
PostGIS image, Compose project, container, volume, unit, principals, sockets,
or firewall from development state. Never stop unrelated shared services.

Implement and validate the fail-closed target runtime and lock contract. If
production identities remain unauthorized or unknown after every safe
repository and isolated gate passes, terminalize as
`EXECUTED-HOLD-PRODUCTION-IDENTITY`. Never apply a proposal that might recreate
or detach the database.
