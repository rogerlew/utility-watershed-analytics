# DB11 — Release-tool CLI and reproducible image

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB11`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-17. Authority covers repository changes and isolated image builds/tests
on `forest1`; it does not cover production, publication, commit, or push.

## Objective

Create the stable command and image foundation that successor packages can fill
in without changing operator-facing command names, error semantics, log schema,
or the code-only image boundary.

## Scope

Included:

- `prepare`, `validate`, `plan`, `build`, `apply`, `rollback`, `recover`, and
  `status` command dispatch;
- stable named exit codes and newline-delimited JSON events;
- verified read-only JSON input and optional exact SHA-256 enforcement;
- explicit fatal `not-implemented` outcomes for successor-owned behavior;
- repository-root image build with an immutable base image digest;
- non-root, read-only, network-disabled digest-pinned runtime proof;
- image-content audit excluding manifests, plans, credentials, source data, and
  repository metadata; and
- unit tests, reproducible double-build proof, CI, operator documentation, and
  package evidence.

Excluded:

- source discovery, artifact fetching/caching, transformations, planning,
  database staging/mutation, rollback, or recovery implementation;
- real release manifests, plans, artifacts, source data, credentials, or
  production access;
- registry publication or image push; and
- commit, branch push, or pull request.

## Authority and inputs

- Governing roadmap: `docs/ROADMAP.md`, DB11.
- Architecture: `docs/database-deployment-architecture.md`, sections 12–14.
- DB08 schemas: `data-releases/schema/v1/`.
- DB09 coordinates: `docs/database-fingerprint-plan-contract.md`.
- Starting revision: `0bd5dc5c735df1ba98073cab362dbf3bf5912d7f`.
- Base image index digest:
  `python:3.12.9-slim-bookworm@sha256:48a11b7ba705fd53bf15248d1f94d36c39549903c5d59edcfa2f3f84126e7b44`.
- Observed execution platform: `linux/amd64`.

## Decisions

- DB11 provides framework behavior only. Commands owned by later packages must
  fail with a stable machine-readable `command_unavailable` result rather than
  report false success.
- `validate` is the only input command implemented here: it verifies a regular
  read-only JSON file and, when supplied, its exact SHA-256. Domain schema and
  cross-file validation remain DB21.
- `status` reports tool version, command availability, and the exit-code map
  without inspecting a database, network, or host configuration.
- The image copies only the release-tool Python package. Release-specific files
  enter later invocations as verified read-only mounts.

## Plan

1. Freeze CLI, log, exit-code, and image contracts.
2. Implement the standard-library command package.
3. Add isolated CLI and failure-path tests.
4. Build the root-context image twice and compare IDs.
5. Audit and execute the image by immutable ID.
6. Reconcile authoritative docs, roadmap, CI, and evidence.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch: `agent/database-backup-deployment-spec`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository, public base-image registry reads, and
  isolated Docker builds/tests on `forest1`
- Mutation boundary: release-tool package, image definition/audit, tests, CI,
  DB11 documentation, roadmap, catalog, and package evidence

## Gates

- CLI unit tests cover all commands, JSON log schema, exit codes, integrity
  mismatch, malformed/missing input, and internal error containment.
- Two clean builds from the same repository context and arguments have the same
  image ID.
- Image audit proves non-root execution and absence of prohibited project
  content.
- Invocation by immutable image ID uses `--read-only`, `--network none`, and a
  read-only bind mount; correct digest passes and wrong digest fails distinctly.
- Python syntax, Ruff, Dockerfile/build, workflow YAML, documentation links and
  fences, secret-pattern scan, and `git diff --check` pass.

Skipped:

- server/client/database suites: no application or database code changes;
- real release/schema/plan behavior: owned by successor packages;
- registry digest: image publication is not authorized, so the accepted local
  immutable image ID is the strongest available Ran evidence.

## Exit criteria

`EXECUTED-COMPLETE` requires all eight commands, stable logs/codes, verified
read-only input proof, reproducible and audited code-only image evidence, CI and
authoritative documentation, and no false claim that future commands work.

Legitimate hold outcomes:

- `EXECUTED-HOLD-IMAGE`: the pinned image cannot build reproducibly or pass the
  content audit;
- `EXECUTED-HOLD-CONTRACT`: stable command/error semantics cannot be frozen
  without a successor decision.

## Risks and recovery

- Risk: a stub command reports success and downstream automation mutates state
  under a false assumption.
  - Prevention: every unavailable command exits with code 20 and a structured
    fatal event.
- Risk: release inputs or `.env` contents enter the image build context/layers.
  - Prevention: Dockerfile-specific allowlist context and explicit image audit.
- Risk: image tags drift.
  - Prevention: base digest pin plus invocation by the built image ID.

## Artifacts

- `artifacts/db11-validation-evidence.md` — sanitized command, build, image,
  audit, and test evidence.

## Execution record

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Base-image manifest inspection | Docker Hub via forest1 Buildx | Ran | Python 3.12.9 slim-bookworm index digest and linux/amd64 platform resolved before authoring. |
| `PYTHONPATH=release-tool python3 -m unittest discover -s release-tool/tests` | forest1 | Ran | Twelve CLI tests passed across all commands, success/error events, inputs, digest mismatch, and contained internal error. |
| `python3 -m unittest scripts.tests.test_verify_release_tool_image` | forest1 | Ran | Four prohibited-path audit tests passed. |
| Initial two direct Docker builds | forest1 default Docker driver | Ran | Honest failure: COPY-generated directory timestamps caused different image IDs. |
| Layer metadata comparison | forest1 Docker save inspection | Ran | Package bytes matched; only generated destination-directory mtimes differed. |
| `scripts/build_release_tool_image.sh uwa-release-tool:db11` | forest1 isolated BuildKit | Ran | Two no-cache normalized builds produced the same image ID `sha256:810d9f...eb2e`. |
| `scripts/verify_release_tool_image.py --image sha256:810d9f...eb2e` | forest1 Docker | Ran | 6,574 rootfs entries audited, one project file scanned, non-root user verified, correct digest passed, wrong digest exited 11, and `apply` exited 20. |
| Python, Ruff, shell syntax, YAML, documentation, secret-pattern, and diff checks | forest1 / temporary validation environment | Mixed | All applicable gates passed; ShellCheck was unavailable. |

## Findings and deviations

- Docker's default image exporter did not produce identical COPY-layer IDs even
  with normalized input mtimes and `SOURCE_DATE_EPOCH`. The final build script
  uses an isolated BuildKit container with `rewrite-timestamp=true`; this is the
  smallest gate that proves the actual image ID, not merely equal filesystems.
- The image copies one self-contained standard-library CLI file. This narrows
  the audit boundary and avoids installing dependencies before successor
  packages establish their exact toolchain needs.
- The accepted image ID is local evidence only because registry publication was
  not authorized.

## Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria: met
- Successor: DB12 artifact client/cache

## Closeout checklist

- [x] Status and evidence mode are accurate.
- [x] Applicable gates and skipped gates are recorded.
- [x] Image and evidence contain no prohibited project content or secrets.
- [x] Authoritative documentation, roadmap, and catalog are reconciled.
- [x] Commit and push remain within recorded authority.
