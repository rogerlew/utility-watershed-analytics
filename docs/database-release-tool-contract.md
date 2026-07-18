# Database release-tool foundation contract

Status: accepted version 1 foundation

Date: 2026-07-17

DB11 freezes the command names, event envelope, exit codes, verified-input
boundary, and reproducible image build. It does not implement release
preparation, planning, materialization, database mutation, rollback, or recovery.

## 1. Commands

The operator entry point is `data-release` in the image and
`python3 -m uwa_release_tool` with `release-tool` on `PYTHONPATH` in a checkout.

| Command | DB11 behavior | Successor owner |
| --- | --- | --- |
| `prepare` | Fatal `command_unavailable`. | DB17–DB19 |
| `validate` | Verify a regular JSON object and optional exact SHA-256. | DB21 extends domain validation. |
| `plan` | Fatal `command_unavailable`. | DB22 |
| `build` | Fatal `command_unavailable`. | DB20 |
| `apply` | Fatal `command_unavailable`. | DB23 |
| `rollback` | Fatal `command_unavailable`. | DB22–DB24 |
| `recover` | Fatal `command_unavailable`. | DB23–DB24 |
| `status` | Report version, command availability, and exit-code names. | Later packages add state without changing the envelope. |

Unavailable commands never report success. Successor packages may implement
them without renaming them or reusing an existing exit code for a different
meaning.

## 2. Exit codes

| Code | Stable name | Meaning |
| --- | --- | --- |
| `0` | `ok` | Command completed successfully. |
| `2` | `usage` | Arguments or command syntax are invalid. |
| `10` | `input` | Required input is missing, unreadable, non-regular, or not read-only when required. |
| `11` | `integrity` | Input bytes differ from the required digest. |
| `12` | `contract` | Input is not valid UTF-8 JSON with an object root. |
| `20` | `command_unavailable` | Command is reserved but not implemented by the current image. |
| `30` | `state_conflict` | Reserved for active/base/lease state conflicts. |
| `40` | `mutation_refused` | Reserved for a fail-closed mutation safety refusal. |
| `70` | `internal` | Unexpected internal error; details are not exposed. |

## 3. Structured events

Command events are newline-delimited JSON. Every event contains:

- `schema_version: 1`;
- `tool: "data-release"`;
- `tool_version`;
- `event`, `level`, and `command`; and
- result or error fields appropriate to that event.

Commands emit `command.start` and then either `command.result` or
`command.error`. Errors include numeric `exit_code`, stable `exit_name`, and
machine-readable `error_code`. Arguments, file contents, environment values,
credentials, and internal exception details are not logged.

## 4. Verified input

DB11 implements:

```bash
data-release validate \
  --input /inputs/release.json \
  --sha256 <64-lowercase-hex> \
  --require-read-only
```

The command rejects symlinks and non-regular files, optionally requires all
filesystem write bits to be absent, hashes the exact bytes, compares the
expected digest before parsing, and accepts only a JSON object root. This is
structural foundation proof, not DB21 release-domain validation.

## 5. Image contract

Build from the repository root with:

```bash
scripts/build_release_tool_image.sh uwa-release-tool:db11
```

The build:

- pins `python:3.12.9-slim-bookworm` by immutable index digest;
- creates a normalized allowlisted context containing only the Dockerfile and
  the self-contained CLI file;
- uses an isolated BuildKit container and source-epoch layer rewriting;
- performs two no-cache builds and requires identical image IDs;
- runs as numeric non-root user `65532:65532`; and
- audits the complete root filesystem for prohibited project paths and scans
  the copied project file for credential markers.

The accepted forest1 build produced local immutable image ID:

```text
sha256:810d9f24d1020c508c80cf165013fbb2740d73a76238d23754f56b638690eb2e
```

This local ID is evidence for the exact DB11 working tree. It is not a published
registry digest and must not be embedded in a real release. A later release
builds its reviewed code/toolchain image first, resolves that exact digest, then
creates manifests and plans that reference it.

## 6. Runtime boundary

The accepted proof invokes the image by immutable ID with:

- `--read-only` root filesystem;
- `--network none`;
- a single read-only input bind mount;
- no environment secrets; and
- exact SHA-256 verification.

The image contains no repository `.env`, Git metadata, data-release directory,
fixture, release manifest, forward/rollback plan, server/client tree, or source
data. Successor packages must preserve this separation even as the pinned
toolchain expands.
