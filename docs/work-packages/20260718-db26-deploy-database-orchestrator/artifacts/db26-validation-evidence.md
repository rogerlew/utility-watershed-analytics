# DB26 validation evidence

Date: 2026-07-18

Environment: `forest1`, repository
`/workdir/utility-watershed-analytics`, branch
`agent/database-backup-deployment-spec`, starting revision `c89a22e`
(`Complete DB25 deployment serialization`).

Evidence mode: Mixed. Local process, filesystem, Docker-image, systemd static,
and test commands are Ran. Production installation/runtime and phase-program
binding are Static and explicitly outside authority.

## Durable orchestration proof

The end-to-end acceptance suite used one preprovisioned real `flock` file,
read-only synthetic request/release/member/forward/inverse files, a fake
mode-`0600` secret file, and a bounded fixture adapter enabled only by
`UWA_DB_DEPLOY_TEST_MODE=1`. Three test methods covered the required and negative
dispositions:

```text
test_fixed_adapter_contract ... ok
test_interruption_crash_reboot_and_lost_client ... ok
test_success_noop_and_failures ... ok

Ran 3 tests
OK
```

Success required recovery, preflight, classification, preparation, staging,
compatibility, backup SHA-256, verified publication receipt, apply activation,
smoke, refresh, report, archive, and cleanup. The verified no-op call trace did
not contain backup, publish, apply, rollback, or refresh.

Injected backup failure and stale base stopped before apply. Injected
post-activation smoke failure invoked rollback, rollback smoke, and refresh and
finished `rolled_back`; an injected inverse failure finished
`rollback_failed`. An injected off-host report-archive failure changed an
otherwise activated success to terminal `failed`. None retried automatically.

TERM left explicit `interrupted` state. SIGKILL simulated both runner process
loss and a host reboot boundary. A new process with the same immutable request
resumed each case, ran recovery again before progressing, and completed. A
detached process completed after its launching client stopped observing it.
State and report files remained readable without SSH or tmux.

All operation directories were mode `0700`; state, per-phase result, report,
and log files were mode `0600`. An expired synthetic terminal directory was
removed under the configured 30-day rehearsal retention while current and
nonterminal state were retained. Terminal reports copied to the forest1-local
archive fixture. The production contract uses the restricted transport to
`forest1:/wc1/utility-watershed-analytics-db-deployment-reports`.

## Unit and image proof

`systemd-analyze verify` accepted
`utility-watershed-analytics-database-deploy@.service`. It emitted only an
unrelated warning about the executable bit on an existing host unit. Static
review confirmed root principal, oneshot type, `Restart=no`, no boot target,
eight-hour start timeout, two-minute stop timeout, mixed kill mode, private
umask, and journal persistence.

The exact release-tool image audit passed for:

```text
sha256:14fd35b2cbfeac308cd796e466af1acf59c29f5e70ddea72cfa950a057217b42
status=passed user=65532:65532 wrong_digest_exit=11 unavailable_exit=20
```

The audit rechecked its nonroot user, read-only digest-bound invocation,
wrong-digest failure, unavailable mutation boundary, project-file contents,
and absence of prohibited source/secret paths. The exact DB25 production
server image
`sha256:2e355618f60d3d7b4107a52de1599ce49f26fb38cad2819601d9213b5b46efcf`
passed `manage.py check --deploy --fail-level ERROR`; its 14 previously recorded
Django/schema/security warnings remained warnings.

Bash syntax, Python compilation, and `git diff --check` passed. ShellCheck was
not installed on `forest1`, so that gate is recorded unavailable rather than
claimed.

## Boundary and cleanup

- `wepp3` was not contacted.
- No real release, plan, source input, database, backup, restic repository,
  credential, service, workflow, activation, rollback, or worker was used.
- No unit was installed, enabled, or started.
- No credential value, `.env`, dump, row-level record, PII, or real coordinate
  was recorded.
- Disposable state, request, secret, lock, adapter, archive, and interruption
  fixtures were removed by the tests. Python bytecode caches were removed.
- DB26 was not committed or pushed during governed execution; DB25 publication
  was the separately authorized first action in this turn.
