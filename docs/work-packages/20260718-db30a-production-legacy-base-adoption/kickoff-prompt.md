# Kickoff prompt — DB30A production legacy-base adoption

Execute `docs/work-packages/20260718-db30a-production-legacy-base-adoption/package.md`
from `forest1` at starting revision `2264735`.

Preflight `wepp3` read-only. Before any production database mutation, create
and independently verify a fresh encrypted backup on operator-owned
`forest1:/wc1`. Restore it into isolated PostGIS, assign the exact reviewed
126-member stable identities, export the immutable legacy baseline, rebuild it
source-independently, and pass adoption/verification/rollback/fallback/adoption.

Bootstrap only the accepted durable DB28 RHESSys capabilities for Gate Creek,
Sooke09, and Sooke15. Do not infer Mill Creek or SBS assets. Under the canonical
shared production lock, repeat identity assignment, export, and adoption only
after the rehearsal passes. Verify unchanged serving/non-watershed rows,
fingerprints, APIs, runtime, and exact active baseline.

Do not replace/add/remove watershed data, deploy code/schema, reboot, select a
provider, delete retained artifacts, dispatch a workflow, commit/push DB30A, or
open a PR. On any mismatch, roll back only through the rehearsed exact adoption
rollback and stop on hold.
