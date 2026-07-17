# Agent Guide

## Authoring ownership

Agents have authoring ownership of this repository. When assigned a task, make
the repository changes needed to deliver a complete, coherent result; do not
stop at suggestions, sample snippets, or a review unless the task explicitly
asks for those only. This ownership includes source code, tests, documentation,
configuration, migrations, and supporting scripts affected by the task.

Own the result end to end: inspect the relevant context, make reasonable
decisions, keep related artifacts in sync, validate the work, and clearly
report any checks that could not be run. Ask for clarification only when a
decision cannot safely be inferred and would materially change the outcome.

Authoring ownership is limited to the repository working tree. It does not
grant permission to access or mutate production, use secrets, push branches,
open pull requests, or change external systems. Those actions require explicit
authority. In particular, roadmap entries and repository changes do not
authorize production operations; follow `docs/ROADMAP.md` and
`docs/work-packages/README.md` for work-package and operational boundaries.

## Environment boundaries

- `forest1` is the shared development server. Use it for repository authoring,
  builds, tests, and explicitly isolated non-production rehearsals. Account for
  other projects before binding ports, allocating storage, or changing shared
  host services.
- `wepp3` is the production server. Do not inspect or mutate it without the
  corresponding explicit production authority, even when a command is
  read-only.
- Never treat observations from `forest1` as evidence of `wepp3` state. A
  successful render or rehearsal of `compose.prod.yml` on `forest1` is Static
  or non-production evidence only.

## Repository map

- `client/`: React and TypeScript application built with Vite; tests use Vitest.
- `server/`: Django, Django REST Framework, and GeoDjango application.
- `docs/`: architecture, inventory, roadmap, and governed work-package records.
- `compose.yml`: development stack.
- `compose.prod.yml`, `Caddyfile`, and `utility-watershed-analytics.service`:
  production integration; editing them is repository work, running them against
  production is an external mutation.
- `.github/workflows/`: authoritative CI and deployment command definitions.

## Working agreements

- Preserve unrelated user changes. Never discard or rewrite work outside the
  assigned scope merely to simplify a patch.
- Fix root causes and keep changes focused. Follow established patterns before
  introducing new abstractions, dependencies, or tooling.
- Update tests and documentation whenever behavior, commands, configuration,
  schemas, or operational assumptions change.
- Do not commit credentials, `.env` files, production data, database dumps, or
  bulky generated artifacts.
- Treat the database inventory and deployment architecture as authoritative for
  their stated subjects. Put durable facts in authoritative documents rather
  than only in a work-package execution record.
- Do not create, execute, or expand a governed work package without following
  its recorded scope, dependencies, gates, dispatch coordinates, and mutation
  authority. Record evidence as Ran, Static, or Mixed without overstating it.

## Validation

Run the narrowest relevant checks first, then broaden when practical. Use the
workflow files as the source of truth for exact CI behavior.

- All changes: `git diff --check`.
- Client changes, from `client/`: `npm run lint`, `npx tsc -b --noEmit`, and
  `npm run test`; use `npm run build` when build behavior is affected.
- Server changes: `ruff check --no-cache` and `python manage.py test` in the
  configured server/container environment described by
  `.github/workflows/server-ci.yml`.
- Shell changes: run the applicable shell syntax check and ShellCheck when it is
  available.
- Documentation changes: verify referenced paths, links, commands, and code
  fences against the current tree.

Do not fix unrelated failures. Report the command, environment, and failure
clearly when a relevant check cannot pass or cannot be run.
