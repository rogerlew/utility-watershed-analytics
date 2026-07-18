# DB19A kickoff prompt

Execute DB19A from revision
`3d82885a2546ed689af78a85ac49a8d597be2d26` on branch
`agent/database-backup-deployment-spec` in
`/workdir/utility-watershed-analytics` on `forest1`.

Centralize RHESSys and release-declared SBS eligibility in one runtime resolver.
When `ActiveDataRelease` is `ACTIVE`, resolve only enabled, public, internally
coherent `RunCapability` rows from that exact active release. Catalog, tile,
geometry, dynamic query, and SBS paths must use declared durable artifact URIs
and metadata. Absent, disabled, checksum/index/geometry-incoherent rows fail
closed without upstream probing.

While the singleton is `EMPTY`, retain only the reviewed existing compatibility
behavior: explicit RHESSys run allowlist and existing-watershed SBS fallback,
with observable log events. The fallback must disappear atomically on `ACTIVE`.
Expose capability metadata to the client and remove client-owned RHESSys run,
scenario, variable, geometry, and Parquet path authority.

Use synthetic fixtures and isolated forest1 database/client tests only. Do not
access `wepp3`, inspect real upstream assets, publish real artifacts, activate a
real release, commit, push, or open a pull request.
