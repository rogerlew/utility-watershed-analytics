# DB12 — Content-addressed artifact client and cache

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB12`

Evidence mode: Mixed

Execution authorization: The operator authorized scaffold and execution on
2026-07-17. Authority covers repository changes, isolated tests, image builds,
and a temporary acceptance subtree under the existing forest1 test namespace.

## Objective

Implement the simple local-filesystem artifact client consumed by later release
commands: verified streaming publication, immutable fetch, corruption-safe
cache promotion, and bounded cache cleanup.

## Scope

Included:

- SHA-256 content key validation and immutable exact lookup;
- streaming publish through a hidden temporary file with atomic no-overwrite
  promotion;
- streaming fetch with checksum verification and atomic cache promotion;
- verification of every cache hit and corrupt-entry quarantine/recovery;
- safe concurrent fetches of the same object;
- bounded cache-only cleanup with retained and leased digest exclusions;
- typed missing, integrity, conflict, input, and permission failures;
- standard-library unit/integration tests and a temporary real-`/wc1` acceptance
  run; and
- release-tool image inclusion, reproducible rebuild, content audit, CI,
  authoritative documentation, roadmap, catalog, and evidence.

Excluded:

- cloud providers, credentials, credential rotation, IAM roles, buckets, or
  network services;
- automatic deletion from the artifact backup store;
- real release artifacts or persistent changes to the DB10A test fixtures;
- production namespace or `wepp3` access;
- CLI publication/fetch commands, source discovery, materialization, database
  mutation, or registry publication; and
- commit, push, or pull request.

## Authority and inputs

- Operator decision: use `forest1:/wc1`; no paid provider or credential model.
- DB10/DB10A contract: `docs/database-artifact-store-contract.md`.
- DB11 foundation: `docs/database-release-tool-contract.md`.
- Storage policy: `data-releases/storage-contract/v1/artifact-store-policy.json`.
- Starting revision: `722d414e3b30f7f51382da4c7b3afd66ab737fe6`.
- Accepted test namespace:
  `/wc1/utility-watershed-analytics-artifacts/v1/test`.

## Decisions

- DB12 is a Python library, not a new operator command. DB11's eight command
  names remain unchanged; successor commands call this library.
- The backup store is authoritative; cache entries are disposable and always
  verified before use.
- The client has no artifact-delete API. Cleanup is limited to exact cache files
  and cannot cross into the backup store.
- The cloud-era credential-rotation and cross-role roadmap checks are replaced
  by owner/mode permission denial and test/production path isolation, matching
  the operator's authoritative DB10A design.
- Acceptance uses a temporary directory below the real test namespace and
  removes it after verification. Production remains untouched.

## Plan

1. Freeze local client, cache, error, and cleanup semantics.
2. Implement streaming publish/fetch and exact digest paths.
3. Add corruption, interruption, concurrency, permission, and cleanup tests.
4. Run the same suite under a temporary real `/wc1` test directory.
5. Rebuild/audit the release-tool image reproducibly.
6. Reconcile documentation, roadmap, CI, evidence, and package status.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch: `agent/database-backup-deployment-spec`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: do not push
- Pull-request target: do not open a PR
- Authorized systems: repository, isolated Docker on forest1, and a temporary
  subtree under `/wc1/utility-watershed-analytics-artifacts/v1/test`
- Mutation boundary: DB12 code/tests/docs/CI and temporary test artifacts/cache
- Production server and production artifact namespace: not authorized

## Gates

- Unit/integration tests cover streaming publication/fetch, exact digest paths,
  interruption, wrong checksum, corrupt cache recovery, concurrent fetch,
  missing object, permission denial, store conflict, environment isolation,
  no store-delete surface, and bounded cleanup/lease protection.
- Temporary real-`/wc1` acceptance passes and leaves no acceptance subtree.
- Two no-cache normalized image builds have the same image ID.
- Image audit proves both CLI and artifact client code are present while release
  manifests, plans, credentials, source data, and repository metadata are absent.
- Python syntax, Ruff, workflow YAML, documentation links/fences,
  secret-pattern scan, and `git diff --check` pass.

Skipped:

- credential rotation and cloud cross-role tests: no credentials or roles exist
  in the binding single-operator contract;
- server/client/database suites: no application or database behavior changes;
- production acceptance: explicitly outside authority and unnecessary for a
  filesystem library tested on the accepted forest1 filesystem.

## Exit criteria

`EXECUTED-COMPLETE` requires the complete library behavior, all failure and
concurrency gates, real-filesystem acceptance with cleanup, reproducible audited
image proof, and reconciled authoritative documentation.

Legitimate hold outcomes:

- `EXECUTED-HOLD-INTEGRITY`: publish/fetch/cache cannot fail closed under an
  injected interruption or digest mismatch;
- `EXECUTED-HOLD-FILESYSTEM`: accepted forest1 test storage cannot exercise the
  required behavior safely.

## Risks and recovery

- Risk: partial bytes become authoritative.
  - Prevention: hidden unique temporaries and promotion only after full digest
    verification.
- Risk: corrupt cache bytes are served.
  - Prevention: verify every hit, quarantine exact corrupt entry, and refetch.
- Risk: cleanup deletes required bytes or touches backup storage.
  - Prevention: cache-root confinement, retained/leased exclusions, deterministic
    preview, and entry/byte limits.
- Risk: concurrent writers race.
  - Prevention: exact digest identity, exclusive link promotion for store
    objects, and atomic verified replacement for cache entries.

## Artifacts

- `artifacts/db12-validation-evidence.md` — sanitized test, real-filesystem,
  image, and validation evidence.

## Execution record

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| DB10A/DB11 contract and roadmap reconciliation | repository | Static | Obsolete credential/role proof replaced by the binding single-operator permission and namespace boundary. |
| `PYTHONPATH=release-tool python3 -m unittest discover -s release-tool/tests` | forest1 | Ran | Twenty-nine CLI/artifact tests passed, including 17 artifact client/cache cases. |
| `python3 -m unittest scripts.tests.test_accept_artifact_client` | forest1 temp filesystem | Ran | Acceptance wrapper passed and left its workspace empty. |
| `scripts/accept_artifact_client.py --workspace /wc1/.../test` | forest1 ZFS | Ran | 2,031,616-byte fixture, 16 concurrent fetches, eight negative/boundary checks, bounded cleanup, and complete temporary-subtree removal passed. |
| `scripts/build_release_tool_image.sh uwa-release-tool:db12-closeout` | forest1 isolated BuildKit | Ran | Two no-cache normalized builds produced identical image ID `sha256:da87d2...ff79`. |
| Release-tool image audit and immutable-ID runtime | forest1 Docker | Ran | 6,579 rootfs entries and four project files audited; no prohibited content; non-root/read-only/no-network verification passed. |
| Python syntax, Ruff, shell syntax, YAML, docs, secret-pattern, and diff gates | forest1 / temporary validation environment | Mixed | All applicable checks passed; ShellCheck was unavailable. |

## Findings and deviations

- The roadmap still named credential rotation and cloud role boundaries from the
  superseded provider design. The proof was corrected to permission denial,
  environment path isolation, and absence of a store-delete API.
- Intermediate directories initially risked inheriting the host umask. The
  implementation now identifies every newly created component and applies mode
  `0700`; tests verify the complete store/cache path.
- Cache cleanup ignores symlinked prefix directories and can never address the
  store root. Store object deletion remains manual and outside this API.
- The real forest1 run used only a temporary subtree. Counts before and after
  were zero, and production remained mode `0700` and untouched.

## Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria: met
- Successor: DB13 and DB17 may consume the client; DB21 extends validation.

## Closeout checklist

- [x] Status and evidence mode are accurate.
- [x] Applicable gates and skipped gates are recorded.
- [x] Real acceptance leaves no temporary test subtree.
- [x] Image/evidence contain no secrets or real release data.
- [x] Authoritative docs, roadmap, and catalog are reconciled.
- [x] Commit and push remain within recorded authority.
