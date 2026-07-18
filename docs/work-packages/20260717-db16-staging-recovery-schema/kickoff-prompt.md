# DB16 kickoff prompt

Work in `/workdir/utility-watershed-analytics` from
`agent/database-backup-deployment-spec` at
`17c0626dc7d8d8ca8cbd737861086bb75a7f5202`, keeping the same working branch.
Do not push and do not open a pull request.

Read first:

- `AGENTS.md`;
- `docs/work-packages/20260717-db16-staging-recovery-schema/package.md`;
- `docs/database-domain-integrity-contract.md`;
- `docs/database-release-ledger-contract.md`; and
- `docs/database-deployment-architecture.md` sections 14.4, 16, and 17.3.

Implement only DB16's fixed logged staging state/tables, bounded loaders,
capacity preflight, expired-attempt recovery, cleanup retry, tests, and durable
documentation. Use isolated disposable PostGIS and temporary files on forest1.
Do not access or mutate `wepp3`, write the production `/wc1` namespace, use real
release data, reconcile or activate serving data, run backups, dispatch
workflows, or add provider/cloud infrastructure.

Close only when the five-table migration, exact capacity sum, bounded batch
proof, concurrent/expired attempt behavior, planning/staging/applying recovery,
retention, cleanup failure/retry, active-serving preservation, scale/reverse
migration, full server gates, and documentation reconciliation pass. Otherwise
use the package's specific hold status and record the first follow-on action.
