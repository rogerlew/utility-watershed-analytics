# DB18 kickoff prompt

Execute `package.md` exactly as authorized.

Start from `bea4a99ca30938b145c6546fcf64ea362a9f59fb`. Implement only the
inventory-defined NASA 202606 `WWS_Code` enrichment in the DB17 preparation
path. Use synthetic public fixtures and the isolated forest1 artifact test
namespace. Preserve target membership, run IDs, geometries, and all
non-enrichment properties exactly.

Do not fetch real NASA inputs, access `wepp3`, publish a real release, invent a
utility-metadata source, copy historical source run IDs or geometry, modify the
legacy loader, or commit/push DB18.
