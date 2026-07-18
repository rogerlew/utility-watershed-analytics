# DB15 kickoff prompt

Work in `/workdir/utility-watershed-analytics` from
`agent/database-backup-deployment-spec` at
`06cb3153f47ede052a8dc3ca06716bbd817a5592`, keeping the same working branch.
Do not push and do not open a pull request.

Read first:

- `AGENTS.md`;
- `docs/work-packages/20260717-db15-release-ledger-capabilities/package.md`;
- `docs/database-release-schema-contract.md`;
- `docs/database-fingerprint-plan-contract.md`;
- `docs/database-watershed-identity-migration.md`;
- `docs/database-domain-integrity-contract.md`; and
- `docs/database-deployment-architecture.md` sections 9, 14, 17, and 18.

Implement only DB15's release ledger and capability-serving schema, bounded
model helpers, tests, and durable documentation. Use isolated disposable
PostGIS on forest1 for execution evidence. Do not access or mutate `wepp3`, use
real releases, fetch external artifacts, activate data, dispatch workflows, or
add provider/cloud infrastructure.

Close only when the singleton bootstrap, release/run/artifact/capability
constraints, attempts and leases, state transitions, failure sanitization,
atomic active capability visibility, forward/reverse migration, full server
gates, and documentation reconciliation pass. Otherwise use the package's
specific hold status and record the first follow-on action.
