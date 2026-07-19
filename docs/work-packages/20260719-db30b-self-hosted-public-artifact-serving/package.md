# DB30B — Self-hosted public artifact serving

Status: `EXECUTED-COMPLETE`

Date: 2026-07-19

Roadmap item: `DB30B`

Evidence mode: Mixed

Execution authorization: On 2026-07-19 the operator requested proceeding with
DB30B after explicitly authorizing the package and confirming temporary
passwordless sudo availability. This authorizes the bounded forest1 and wepp3
reads, self-hosted read-only artifact-serving configuration, fresh encrypted
database backup, exact retained DB30A re-adoption, verification, and rehearsed
rollback defined here. It does not authorize a storage provider, copying the
4.2 GiB namespace to a provider or unrelated host, artifact mutation/deletion,
domain-row mutation, unrelated service/OS changes, reboot, DB31, commit, push,
PR, or workflow dispatch.

## Objective

Serve the existing operator-owned immutable production namespace under
`forest1:/wc1/utility-watershed-analytics-artifacts/v1/production` at its
already-reviewed `https://firewisewatersheds.org/artifacts/v1/production` URI,
prove exact public reads, and re-adopt the retained DB30A baseline without
changing watershed-domain rows or unrelated state.

## Scope

Included:

- a minimal read-only static origin on forest1, reachable only through the
  bounded wepp3-to-forest1 path selected during preflight;
- an exact-path production Caddy route for `/artifacts/v1/production/*`, with
  the frontend/API routes otherwise unchanged;
- immutable-object cache/content-type/range behavior needed by TIFF and
  Parquet clients;
- fresh encrypted database backup independently visible on forest1;
- exact DB30A manifest `bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5`
  and retained release `2026-07-18.30` re-adoption;
- independent public manifest, TIFF, and Parquet size/SHA/media checks, Gate
  Creek query, Sooke09/Sooke15 capability reads, fingerprints, API/runtime
  health, rollback rehearsal, and cleanup.

Excluded:

- external storage/CDN/provider selection;
- artifact generation, mutation, deletion, or relocation;
- serving-domain replacement/addition/removal, inferred capabilities, Mill
  Creek RHESSYS, SBS activation, DB31+, reboot, broad firewall exposure,
  unrelated configuration, commit, push, PR, or workflow dispatch.

## Authority and fixed inputs

- Governing roadmap: `docs/ROADMAP.md`, DB30B.
- DB30A package and exact rollback:
  `../20260718-db30a-production-legacy-base-adoption/package.md`.
- Starting repository revision:
  `d491f0fd46d843be28dce9d146ea0c9e89a4f156`.
- Artifact root:
  `/wc1/utility-watershed-analytics-artifacts/v1/production` on forest1.
- Public base URI:
  `https://firewisewatersheds.org/artifacts/v1/production`.
- Manifest SHA-256:
  `bb9729bc1907f9f81c1e5f52728f889dcf5a129d911ebda454b9d2d5658caea5`.
- Production: wepp3; artifact/backup host: forest1.

## Plan

1. Freeze exact topology, identities, paths, and rollback coordinates.
2. Scaffold and locally rehearse the least-exposed static origin and proxy.
3. Verify a fresh encrypted database backup from wepp3 on forest1.
4. Install and verify the static origin, then the exact Caddy route.
5. Re-adopt the retained manifest under the exclusive operation lock.
6. Verify public objects/capabilities/state and reconcile durable evidence.

## Gates

- Correct hosts, clean checkouts, exact DB30A manifest/artifact root, private
  immutable object permissions, sufficient capacity, and no conflicting route
  or listener.
- The selected forest1 listener is not public and accepts only the intended
  wepp3 path; Caddy configuration validates before replacement or reload.
- Representative manifest, TIFF, and Parquet bytes match local size/SHA and
  correct media types/range reads before database adoption.
- Fresh encrypted backup is independently visible on forest1 before adoption.
- Production starts coherent `EMPTY` with the retained exact validated DB30A
  ledger, zero capabilities, unchanged counts/fingerprints, and healthy legacy
  fallback.
- Adoption recreates only the three reviewed capability rows and active
  pointer/attempt metadata; all serving-domain and unrelated state is unchanged.
- Gate Creek materialized query and Sooke09/Sooke15 reads succeed from durable
  assets; public/API/runtime health and exact fingerprints pass.

## Failure and rollback

- Before adoption: restore the prior Caddy configuration, stop/disable only
  the DB30B origin, verify frontend/API health, and hold.
- After adoption: execute the exact DB30A rollback first, prove coherent
  `EMPTY` and legacy fallback, then restore the prior Caddy configuration and
  stop/disable only the DB30B origin.
- Never modify or delete the retained `/wc1` artifact namespace as rollback.

## Artifacts

- `artifacts/db30b-validation-evidence.md`
- `artifacts/reviewed-adoption-plan.json`
- `artifacts/reviewed-persistence-plan.json`
- `artifacts/db30b_adopt.sh`
- `artifacts/db30b_rollback.sh`
- `scripts/generate_artifact_origin_caddy.py`
- `scripts/tests/test_generate_artifact_origin_caddy.py`
- `ops/systemd/uwa-artifact-origin.service`
- `ops/artifact-serving/apply_artifact_proxy.sh`
- `ops/artifact-serving/ensure_artifact_proxy.sh`
- `ops/artifact-serving/compose.artifact-proxy.yml`
- `ops/systemd/utility-watershed-analytics.service.d/30-db30b-artifact-route.conf`
- Bulky immutable bytes, protected environments, database evidence, and raw
  host output remain outside Git.
- Local ignored administrative log under `docs/sys-administration/logs/`.

## Execution record

| Command or review | Environment | Evidence | Result |
| --- | --- | --- | --- |
| Package scaffold and authority freeze | repository / forest1 | Static | Recorded before host topology inspection. |
| Topology and origin rehearsal | forest1 | Mixed | Generated an allowlisted, read-only Caddy origin for all 996 referenced objects plus the manifest; validation, media mapping, exact reads, restart, Tailscale-only bind, and negative LAN reachability passed. |
| Fresh encrypted database backup | wepp3 to forest1 | Mixed | Snapshot `0d970414ff92497f75ba0ad5bc32f41b61482ab3a5fcbfa3da38858b63886afe`; backup-set SHA-256 `5cb052ae33e3d91f8035143c0a3bc690a26fc9b43a67d681f557a7995d504b4b`; independent metadata and rotating `1/100` data check passed. |
| Exact production proxy deployment | wepp3 | Mixed | Protected Caddyfile/Compose override/helpers and systemd drop-in installed; configuration validation, exact read-only mount, canonical reload, and bounded Caddy restart passed without changing the database identity. |
| Initial adoption and automatic rollback | wepp3 | Mixed | A cache-ownership preflight failed before mutation and was corrected. The first adoption passed DB checks but exposed an HTTP 405 API routing defect; the exact script automatically rolled back to coherent `EMPTY`, and the original route plus 173-row Gate Creek fallback were restored. |
| Corrected adoption and capability checks | wepp3 / public endpoint | Mixed | Nested fallback routing preserved API precedence. Exact manifest `bb9729...` became `ACTIVE`; 126/195457/86895 rows and domain fingerprints were unchanged; Gate Creek returned 173 materialized rows and both Sooke catalogs/tiles passed. |
| Persistence and independent verification | forest1 / wepp3 | Mixed | Origin user service with linger, protected proxy override, systemd start/reload hooks, independent public manifest/TIFF/Parquet SHA/media/range reads, canonical reload, and Caddy-only restart all passed. |
| Cleanup and evidence retention | forest1 / wepp3 | Mixed | Disposable cache, containers, configs, and executor image were removed; intended serving state, immutable `/wc1` namespace, encrypted backup, and mode-`0700` sanitized evidence were retained; production checkout and services are healthy. |
| Repository validation | forest1 / disposable images | Ran | Three generator tests, Ruff, shell syntax, Caddy validation, origin unit verification, Compose read-only mount assertion, JSON parsing, path review, credential scan, and `git diff --check` passed. ShellCheck was unavailable. |

### Findings and deviations

- The first executor preflight rejected the transferred cache because its owner
  UID differed from the container UID. The scripts now derive the bounded
  operation UID/GID; no database mutation occurred before this correction.
- The first live adoption exposed a Caddy ordering defect: a fallback `handle`
  without a nested `route` placed `try_files` ahead of the API proxy. The
  automatic exact DB30A rollback passed, the original configuration was
  restored, and legacy fallback was verified before retry.
- The corrected fallback uses an explicit nested `route`. A local functional
  rehearsal and the second production adoption proved ordinary API POSTs and
  the artifact route together. Failure evidence is retained rather than erased
  by the successful retry.
- No provider was selected or used. Artifacts and encrypted backups remain on
  the operator-owned forest1 `/wc1` infrastructure.

### Terminal disposition

- Final status: `EXECUTED-COMPLETE`
- Exit criteria disposition: the self-hosted route, fresh verified backup,
  exact re-adoption, materialized capabilities, persistence, restart/reload,
  rollback, state-integrity, evidence, and cleanup gates passed.
- Blocker, if held: none
- Successor package: DB31 requires separate dispatch.

## Closeout checklist

- [x] Package status/evidence mode and authority are accurate.
- [x] Serving topology and least-exposure proof are recorded.
- [x] Fresh backup and exact public object reads pass.
- [x] Re-adoption, capability queries, fingerprints, and fallback rollback pass.
- [x] Artifact/configuration permissions and cleanup are verified.
- [x] Authoritative docs, catalog, and roadmap are reconciled.
- [x] Commit/push/PR actions match authorization.
