# Kickoff prompt — <package title>

Use this as a paste-ready execution handoff. Replace every placeholder and keep
its repository coordinates and permissions synchronized with `package.md`.

## Assignment

Execute `<package path>` to its honest terminal state.

Repository: `<path or URL>`

Starting branch or commit: `<exact ref>`

Working branch: `<branch>`

Push target: `<remote/branch or “do not push”>`

Pull-request target: `<owner/repository/base or “do not open a PR”>`

Authorized systems: `<local, staging, production read-only, etc.>`

Mutation boundary: `<files, services, or data that may change>`

## Read first, in order

1. `docs/work-packages/README.md`
2. `docs/ROADMAP.md`
3. `<package path>/package.md`
4. `<governing specifications, inventories, and prior package links>`

## Required outcome

<Restate the objective and checkable exit criteria. Do not broaden the package
from this prompt.>

## Execution constraints

- Stay within included scope and preserve unrelated local changes.
- Do not infer production access, mutation, push, or PR authority from the
  existence of this package.
- Treat observed current state and approved target state as separate claims.
- Record material commands, environment, revision, results, and artifacts as
  work proceeds.
- Label evidence Ran, Static, or Mixed. Do not claim runtime behavior from a
  static inspection.
- Freeze or checksum external inputs required for reproducible results.
- Stop before an unapproved external mutation or destructive operation.
- When the plan changes materially, update the package before continuing.
- Report blockers concretely; do not hide partial execution behind optimistic
  status language.

## Gates and review

Run every applicable gate listed in the package and record the result. Record
each skipped gate with a reason. Request the package's specified review and
disposition every actionable finding in code, documentation, scope, or an
explicit successor package.

## Closeout

Before handing back:

1. Update the execution record, command evidence, findings, artifacts, and
   terminal disposition in `package.md`.
2. Use `EXECUTED-COMPLETE` only when all exit criteria are satisfied. Otherwise
   use a specific `EXECUTED-HOLD-<REASON>`, name the exact blocker, and give the
   first follow-on action.
3. Update `docs/work-packages/README.md` and reconcile `docs/ROADMAP.md`.
4. Update authoritative specifications or inventories for durable facts.
5. Run `git diff --check` and the package-specific gates.
6. Commit, push, or open a PR only to the explicitly authorized targets.

Return a concise summary of the outcome, verification evidence, terminal
status, remaining risks, and exact commit/branch/PR location when applicable.
