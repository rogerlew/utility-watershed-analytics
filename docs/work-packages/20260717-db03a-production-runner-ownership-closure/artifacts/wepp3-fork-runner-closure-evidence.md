# DB03A `wepp3` Fork Runner Closure Evidence

Evidence mode: Ran unless marked Static

Executed: 2026-07-17 America/Los_Angeles

## Outcome

Production automation now belongs to
`rogerlew/utility-watershed-analytics`. The safe workflow was published to the
fork's `main`, the existing protected production runtime was delivered as the
fork's `PRODUCTION_ENV` secret without printing or persisting its values, and a
separate fork-owned runner is online and idle on `wepp3`.

No workflow was dispatched. No application, database, container, image,
volume, data, network, firewall, runtime, backup schedule, or reboot operation
was performed.

## Repository and workflow

- Fork: `rogerlew/utility-watershed-analytics`.
- Verified safe `main` revision before closure evidence publication:
  `8d443171cfa616d0e7941102e299763cb6e8a596`.
- `.github/workflows/deploy.yml` SHA-256:
  `b8db97075bc153e9d569d7bef75e11b3661da35bf703c2393469c2ffc7529a71`.
- The workflow calls `scripts/deploy_application.sh`, uses the shared
  non-cancelling production concurrency group, creates the runtime file with
  mode `0600`, and shreds it during unconditional cleanup.
- The fork has exactly the expected secret name `PRODUCTION_ENV`; no secret
  value or value hash was read back or recorded.
- Queued and in-progress run counts remained zero before registration, before
  service start, and at closeout. This package created no Actions run.

## Runner installation and ownership

- Runner release: GitHub Actions runner `2.335.1`.
- Official archive SHA-256:
  `4ef2f25285f0ae4477f1fe1e346db76d2f3ebf03824e2ddd1973a2819bf6c8cf`.
- Installation: `/workdir/actions-runner-rogerlew`, owned by `gha`.
- Service:
  `actions.runner.rogerlew-utility-watershed-analytics.wepp3.service`.
- Service state: enabled and active as `gha`.
- GitHub state: runner `wepp3` online, idle, with labels `self-hosted`, `Linux`,
  `X64`, and `deploy`.
- The service process inherited GID `996` (`uwa-operators`).
- The old local upstream-owned service remains disabled and inactive:
  `actions.runner.brandonxu360-utility-watershed-analytics.wepp3.service`.
- No deployment checkout or `.env.production-runtime` was created because no
  job ran.

The first archive checksum read was attempted as `roger` and was denied by the
mode-`0750` runner directory. The check was repeated as `gha`, matched the
official digest exactly, and only then was the archive extracted. This was a
permission-safe command correction, not a weakened directory mode.

## Unchanged production invariants

- Database container:
  `d2f0c406fc2bf02d5461b88d6f803112da1c9933494c2c6a68bf829268898bf2`.
- Database image:
  `sha256:612b68f8c521abc35c0258475c187855c6d37cb10b6dfe090d792706fcd59a46`.
- Anonymous database volume:
  `be7d3b8f6a3b08f300d2d3c45554e088eacce531a781d95bdff2fc9e32e22d51`.
- Database state: running, healthy, restart count zero.
- Safe runtime unit: enabled and active.
- Backup and backup-freshness timers: active.
- Host port 8000: no listener.
- Public root, public API schema, and canonical-host admin login: HTTP 200.

Temporary passwordless sudo was removed after verification and the remaining
sudoers configuration parsed successfully. The fork-owned runner remained
online and idle afterward.
