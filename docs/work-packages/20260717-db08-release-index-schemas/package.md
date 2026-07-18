# DB08 — Versioned release and index schemas

Status: `EXECUTED-COMPLETE`

Date: 2026-07-17

Roadmap item: `DB08`

Evidence mode: Mixed

Execution authorization: The user authorized scaffold and execution on
2026-07-17, initially limited to repository changes and local validation on
`forest1`. The user separately authorized commit and push on 2026-07-17.
Production access or mutation and pull-request actions are not authorized.

## Objective

Encode the accepted DB07 decisions in a compact version-1 schema suite for
release manifests, exact member indexes, artifact references, transformation
lineage, RHESSys capability indexes, validation reports, and compatibility
envelopes, with CI-ready positive and negative proof.

## Scope

Included:

- Draft 2020-12 JSON Schemas with stable versioned identifiers;
- exact artifact checksum/size/media-type references and safe HTTPS locations;
- release, collection, member, removal, source-authentication, and compatibility
  structure;
- exact batch membership and expected count/bounds structure;
- transformation inputs/output, field decisions, join keys, counts, and report
  reference;
- dynamic/precomputed RHESSys asset declarations;
- sanitized validation-report structure;
- structural and semantic validation for identity uniqueness, exact removals,
  version compatibility, secret boundaries, and fixture coverage;
- representative valid fixtures and focused invalid cases; and
- a pull-request CI workflow plus standard-library tests around the validator.

Excluded:

- DB09 fingerprint canonicalization or deployment plan schemas;
- DB10 artifact-provider, bucket, IAM, KMS, retention, or object-lock choices;
- actual release manifests, production member assignments, artifact uploads,
  external fetches, database models/migrations, loader/reconciler behavior, or
  deployment; and
- credentials, credential-bearing URLs, mutable unverified inputs, raw data,
  or production access.

## Authority and inputs

- Governing roadmap: `docs/ROADMAP.md`, Wave 1 DB08.
- Identity/authority input: `docs/database-identity-metadata-contract.md`.
- Architecture: `docs/database-deployment-architecture.md`, sections 8, 9,
  12, 13, and 17.
- Approved inventory: `docs/database-inventory.md`.
- Starting revision: `c9ab4c90d42817da6343557acb82add5e087c69e`.
- Frozen external inputs: none.

## Assumptions and decisions

- Schema version, data contract, identity contract, and artifact contract are
  all version 1; unknown versions fail closed.
- JSON is the canonical machine format for DB08 fixtures. YAML may be accepted
  later only after parsing into the same JSON data model.
- Every artifact reference requires safe HTTPS URI, SHA-256, byte size, media
  type, and immutable verification assertion. DB10 may add provider-specific
  URI forms in a later compatible version.
- Secret references are uppercase environment-style names. No password, token,
  credential, raw secret, URL query, URL fragment, or URI userinfo is allowed.
- JSON Schema handles structural rules; one deterministic semantic validator
  handles field-based uniqueness and cross-record exactness that JSON Schema
  cannot express.
- DB08 fixtures are illustrative and contain no production membership claim.

## Plan

1. Freeze schema vocabulary, identifiers, and cross-schema references.
2. Implement seven version-1 schemas and semantic validation.
3. Add complete valid fixtures and required negative cases.
4. Run local/CI-shaped gates and reconcile DB09 inputs.

## Execution and dispatch

- Repository: `/workdir/utility-watershed-analytics`
- Starting branch or commit:
  `agent/database-backup-deployment-spec` at
  `c9ab4c90d42817da6343557acb82add5e087c69e`
- Working branch: `agent/database-backup-deployment-spec`
- Push target: `origin/agent/database-backup-deployment-spec`
- Pull-request target: do not open a PR
- Authorized systems: repository and local `forest1` validation only
- Mutation boundary: DB08 schemas, fixtures, validator/tests, CI wiring, and
  authoritative documentation; no runtime, database, data, or external-system
  mutation
- Executor/reviewer: Codex authors and validates; `roger` owns publication and
  any later provider or real-release decision

## Gates

Always:

- `git diff --check` and exact changed-file review;
- every schema passes Draft 2020-12 schema validation;
- every valid fixture passes structural, semantic, and secret-boundary checks;
- every invalid fixture fails at its expected phase and reason;
- schema and invalid-case coverage are exact and deterministic;
- relative Markdown links, JSON syntax, workflow syntax, and referenced paths
  pass; and
- no secret, raw data, external mutable input, or bulky artifact is present.

Applicable negative proof:

- duplicate collection, watershed, or run identity;
- wildcard or target-overlapping removal;
- artifact without immutable verification fields;
- RHESSys mode without its required asset family;
- incompatible contract version;
- credential-bearing URI; and
- raw authentication token instead of `secret_ref`.

Skipped gates and reasons:

- backend/client application suites: no application behavior changes;
- database/data deployment: DB08 defines representation only;
- production checks: DB08 needs no production fact or mutation;
- real object-store verification: DB10 owns provider acceptance.

## Exit criteria

`EXECUTED-COMPLETE` requires:

- all seven schema subjects are versioned and cross-reference successfully;
- valid and invalid suites cover every roadmap rejection requirement;
- CI invokes the same repository validator and tests; and
- architecture, roadmap, catalog, and package evidence are reconciled.

Legitimate hold outcomes:

- `EXECUTED-HOLD-CONTRACT-GAP`: DB07 leaves a schema choice ambiguous; identify
  the exact field and return it to DB07 rather than inventing a default.
- `EXECUTED-HOLD-SCHEMA`: a required invariant cannot be expressed structurally
  or with the bounded semantic validator; record the missing invariant.
- `EXECUTED-HOLD-FIXTURE`: a negative case passes or a valid case fails; preserve
  the smallest case and stop before DB09.

## Risks and recovery

- Risk: schemas look strict but allow duplicate logical identities.
  - Prevention: semantic uniqueness checks plus mutation tests.
  - Recovery: add the smallest failing fixture and semantic rule.
- Risk: a URI or authentication object carries credentials.
  - Prevention: safe-HTTPS patterns, closed objects, recursive secret scan, and
    negative fixtures.
  - Recovery: reject the fixture and narrow the schema or scanner.
- Risk: DB08 prematurely chooses artifact infrastructure or fingerprints.
  - Prevention: provider-neutral verified references; DB09/DB10 remain explicit.
  - Recovery: remove provider/fingerprint behavior and record the successor.

## Artifacts

- `artifacts/db08-validation-evidence.md` — schema inventory, commands,
  valid/invalid coverage, CI check, and results.

Do not store credentials, environment files, production membership, raw data,
database dumps, or large artifacts in this package.

## Execution record

### Commands and evidence

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Package scaffold and authority review | repository / `forest1` | Static | DB07 dependency, seven schema subjects, negative gates, repository-only boundary, and holds frozen. |
| Draft 2020-12 schema and cross-reference validation | temporary Python 3.12 virtual environment / `forest1` | Ran | Seven schemas and seven valid fixtures passed; cross-file collection, count, membership, and ordering matched. |
| Required negative fixture validation | temporary Python 3.12 virtual environment / `forest1` | Ran | Nine cases rejected for their recorded structural or semantic reason. |
| `python -m unittest scripts.tests.test_validate_release_schemas` | temporary Python 3.12 virtual environment / `forest1` | Ran | Seven tests passed, including duplicate run identity and validator fail-closed mutations. |
| JSON, Python, Ruff, workflow YAML, diff, path, link, and secret-pattern review | repository / `forest1` | Mixed | Applicable local gates passed; PyYAML and Actionlint were unavailable, Ruby parsed the YAML, and no server code changed. |
| CI and architecture reconciliation | repository | Static | Reusable data-contract workflow gates deployment; accepted contract, architecture, DB07 handoff, roadmap, and catalog agree. No workflow was dispatched. |
| Publication authority review | repository / GitHub | Static | User authorized commit and push to the current origin branch on 2026-07-17; no PR or production action was requested. |

### Findings and deviations

- The host Python lacked `jsonschema`; execution used a temporary virtual
  environment with the CI-pinned `jsonschema==4.23.0` dependency.
- Credential words and URI user information occur only in deliberately invalid
  illustrative fixtures; all are rejected and contain no real secret.
- The final corpus is provider-neutral and contains no fingerprint algorithm,
  deployment plan, production membership, or external artifact observation.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: all seven schemas, required positive/negative
  proof, semantic cross-checks, CI wiring, and documentation reconciliation
  passed
- Blocker, if held: not applicable
- First follow-on action, if held: not applicable
- Successor package, if any: DB09 after DB08 completes

## Closeout checklist

- [x] Package status and evidence mode are accurate.
- [x] Applicable gates and skipped-gate reasons are recorded.
- [x] Artifacts contain no secrets or prohibited large data.
- [x] Durable findings are reflected in authoritative docs.
- [x] Work-package catalog is updated.
- [x] Forward roadmap is reconciled.
- [x] Commit, push, and PR actions match the recorded authorization.
