# DB25 — Code/data compatibility and deployment serialization

Status: `EXECUTED-COMPLETE`

Date: 2026-07-18

Roadmap item: `DB25`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-18. Authority covers repository changes, workflow/static validation,
synthetic releases and plans, disposable credentials, and disposable PostGIS
on forest1. It excludes `wepp3`, production credentials or roles, production
migrations, production workflow dispatch, real releases/plans, commit, push,
PR, and external mutation.

## Objective

Serialize code, schema, and future data operations at GitHub and host layers;
make production migrations an explicit separately credentialed one-shot; fail
closed on code/schema/release compatibility; and define tested least-privilege
database identities without implementing DB26's production orchestrator.

## Decisions

- Keep `utility-watershed-analytics-production` as the one literal GitHub
  production concurrency group and validate every production workflow against
  it.
- Reuse DB03's canonical host lock and add a small reusable inherited-lock
  assertion for mutation boundaries and lock-loss proof.
- Remove implicit production startup migration. The application entrypoint
  performs only `migrate --check`; application deployment runs one explicit
  migration container using a separate protected credential file.
- Put compatibility rules in Django/Python so application deployment and the
  later database orchestrator call the same code rather than duplicating
  release rules in shell or workflow YAML.
- Separate NOLOGIN privilege roles from LOGIN credential principals. Provision
  grants without passwords; rotate each credential from a protected file.
- Give runtime, status, and staging identities no serving-domain or active
  pointer mutation path. Activation, migration, backup, and restore identities
  receive only their documented operational elevation.

## Gates

- `git diff --check`, Ruff, migration drift, focused DB25 tests, and complete
  server suite in the final production image.
- Shell syntax, ShellCheck when available, workflow/static serialization
  validation, and exact production entrypoint/deploy-script tests.
- Competing code/data lock holders serialize; missing, wrong-mode, wrong-file,
  and lost inherited locks fail closed.
- Stale base, incompatible/pending migration, wrong materializer image/Git,
  unsupported contract, incomplete artifacts/capabilities, and plan mismatch
  fail before activation.
- Disposable PostGIS negative grants and credential rotation cover status,
  staging, activation, runtime, backup, migration, and restore/break-glass.
- Emergency identity has forced statement logging; ordinary identities cannot
  assume privileged roles or bypass reconciliation.
- Normal application startup does not execute migrations.
- Documentation, scope, secrets, links, and disposable cleanup.

## Execution record

- Retained the single production GitHub concurrency group and added a static
  validator that fails any production-environment workflow using another group
  or cancellation policy. DB26/DB27 must pass the same validator when their
  data workflow is added.
- Added a reusable inherited-lock assertion and reasserted DB03's exclusive
  canonical descriptor before migration and worker replacement. Missing,
  stale, wrong-mode, wrong-file, cancellation, contention, and deliberately
  closed descriptors failed closed.
- Removed implicit production startup migration. The entrypoint now performs
  `migrate --check`; application deployment runs one explicit migration with a
  separate mode-0600 `uwa_migration_login` file and checks active-release
  compatibility before replacing workers.
- Added application and staged-release compatibility commands covering pending
  schema state, contract/migration range, deployed application Git, exact
  materializer image/Git, reviewed plan/target/base, required artifacts, exact
  staging, and capability configuration.
- Added seven NOLOGIN privilege roles, seven independently rotatable LOGIN
  principals, convergent bounded grants, protected password-file rotation, and
  forced restore/break-glass statement logging.
- Passed disposable PostGIS permission probes for every allowed/denied boundary
  and two credential generations for every principal. The runtime identity
  passed the exact production image's migration-check-only entrypoint.
- Passed 27 combined DB20–DB25 tests and all 206 server tests in the final
  production image, plus DB08/DB09 validators and tests.
- Used synthetic releases, plans, passwords, and disposable PostGIS only. No
  `wepp3`, production role/credential/migration/workflow, commit, push, PR, or
  external mutation occurred during DB25 execution.

### Commands and evidence

| Gate | Result |
| --- | --- |
| Final production image build | Passed; `sha256:2e355618f60d3d7b4107a52de1599ce49f26fb38cad2819601d9213b5b46efcf` |
| Ruff and migration drift | Passed; no changes detected |
| Focused compatibility proof | 5 passed in 0.849 seconds |
| Combined DB20–DB25 regression | 27 passed in 37.102 seconds; one DB09 repository-schema integration skipped |
| Final-image server regression | 206 passed in 90.655 seconds; one DB09 repository-schema integration skipped because schemas are outside the server image |
| Host lock and deployment shell | Bash syntax, ShellCheck, startup/deploy mocks, contention, cancellation, stale/lost descriptor, and static workflow policy passed |
| Disposable database roles | 7 privilege/login pairs, 7 old-to-new rotations, positive grants, negative grants, and break-glass audit settings passed |
| Runtime-role production entrypoint | Passed `migrate --check`, deploy checks, and command handoff; existing unrelated Django deployment warnings remained warnings |
| DB08 schema contract | Validator plus 7 tests passed |
| DB09 fingerprint/plan contract | Validator plus 12 tests passed |

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: met
- Blocker: none
- First follow-on action: scaffold DB26 production database orchestrator
- Successor package: DB26, not yet scaffolded

## Artifacts

- `artifacts/db25-validation-evidence.md`
- `docs/database-deployment-serialization-contract.md`

## Closeout checklist

- [x] Package status/evidence mode are accurate.
- [x] Gates and skipped reasons are recorded.
- [x] Evidence contains no credentials, real coordinates, or PII.
- [x] Durable findings are reflected in authoritative docs.
- [x] Catalog and forward roadmap are reconciled.
- [x] Commit, push, and PR actions match authority.
