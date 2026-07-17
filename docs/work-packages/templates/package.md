# <Roadmap ID — Package title>

Status: `SCAFFOLDED` | `EXECUTED-COMPLETE` | `EXECUTED-HOLD-<REASON>`

Date: YYYY-MM-DD

Roadmap item: `<ID>`

Evidence mode: Ran | Static | Mixed

Execution authorization: Not authorized | <authority, date, and reference>

## Objective

State the bounded outcome and why it is the next useful unit of work.

## Scope

Included:

- <deliverable or behavior>

Excluded:

- <neighboring work that is deliberately not part of this package>

## Authority and inputs

- Governing specification or inventory: <path and relevant section>
- Starting repository revision: <commit>
- Frozen external inputs and checksums, when applicable: <references>
- Observed state that must be distinguished from the target state: <evidence>

## Assumptions and decisions

- <decision, owner, and rationale or open decision that blocks execution>

## Plan

1. <specification, fixture, or safety preparation before implementation>
2. <implementation or analysis phase>
3. <validation and independent review phase>
4. <closeout, artifact, roadmap, and catalog reconciliation>

## Execution and dispatch

- Repository: <path or URL>
- Starting branch or commit: <exact ref>
- Working branch: <branch>
- Push target: <remote/branch or “do not push”>
- Pull-request target: <owner/repository/base or “do not open a PR”>
- Authorized systems: <local, staging, production read-only, etc.>
- Mutation boundary: <files, services, or data that may change>
- Executor and review assignments: <names or roles>

Every derived kickoff prompt must preserve these coordinates and permissions.

## Gates

Always:

- `git diff --check`
- Package diff reviewed against included and excluded scope.

Select and record all applicable checks:

- Backend: the current commands in `.github/workflows/server-ci.yml`.
- Frontend: the current commands in `.github/workflows/client-ci.yml`.
- Shell: syntax check; ShellCheck when available; safe fixture or dry-run tests.
- Documentation: local links, referenced paths, code fences, and commands.
- Data: schema validation, checksums, exact membership and removal plan,
  empty-build and repeat-apply fingerprints, and application smoke tests.
- Operations: preflight, verified backup, bounded staging test, rollback test,
  logs/report, and postcondition checks within the authorized environment.

Skipped gate and reason:

- <gate>: <why it does not apply or why the package must be held>

## Exit criteria

`EXECUTED-COMPLETE` requires:

- <observable outcome>
- <required evidence and gate result>
- authoritative docs, roadmap, and catalog reconciled

Legitimate hold outcomes:

- `EXECUTED-HOLD-<REASON>`: <specific condition, blocker, and first follow-on>

## Risks and recovery

- Risk: <failure mode>
  - Prevention: <control>
  - Recovery or rollback: <action>

## Artifacts

- `artifacts/` — <planned reports, logs, manifests, review notes, or fixtures>

Do not store secrets, environment files, database dumps, or large source data
in the package directory.

## Execution record

Fill this section during execution.

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| <command> | <host/container/revision> | Ran/Static | <result or artifact> |

### Findings and deviations

- <finding, decision, changed assumption, or deviation from plan>

### Terminal disposition

- Final status: <status>
- Exit criteria disposition: <met or exact unmet criteria>
- Blocker, if held: <exact blocker>
- First follow-on action, if held: <one concrete action>
- Successor package, if any: <link; never reuse this package ID>

## Closeout checklist

- [ ] Package status and evidence mode are accurate.
- [ ] Applicable gates and skipped-gate reasons are recorded.
- [ ] Artifacts contain no secrets or prohibited large data.
- [ ] Durable findings are reflected in authoritative docs.
- [ ] Work-package catalog is updated.
- [ ] Forward roadmap is reconciled.
- [ ] Commit, push, and PR actions match the recorded authorization.
