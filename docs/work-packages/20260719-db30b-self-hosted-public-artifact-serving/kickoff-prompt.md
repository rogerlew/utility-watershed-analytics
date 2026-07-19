# DB30B kickoff prompt

Execute only the DB30B package recorded in `package.md`.

Keep the solution self-hosted and simple: the authoritative immutable bytes
remain on `forest1:/wc1`; do not select a provider or duplicate them to one.
Expose only the reviewed production artifact path, rehearse and validate every
configuration before production replacement, take and independently verify a
fresh encrypted backup before re-adoption, and use the exact DB30A rollback on
any post-adoption failure. Do not mutate serving-domain rows or expand into
DB31, unrelated services, reboot, commit, push, PR, or workflow dispatch.
