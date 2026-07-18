# NASA 202606 enrichment contract

Status: implemented synthetic-proof tooling

Date: 2026-07-17

DB18 implements the fixed transformation specified by the
[production data-source inventory](database-inventory.md). It extends DB17's
[strict preparation path](database-source-preparation-contract.md) without
authorizing or publishing a real NASA release.

## 1. Fixed transform

The only accepted transform identifier is `nasa-202606-wws-code`. It applies
only when:

- `collection_key` is `nasa-roses`;
- every reviewed target run ID starts with
  `batch;;nasa-roses-202606-psbs;;`; and
- the descriptor pins the enrichment source by credential-free HTTPS URL,
  exact SHA-256, positive byte count, code Git commit, and validator image
  digest.

The source bytes must match both size and digest before parsing. DB18 does not
use the inventory's documented public source merely because its coordinates
are known; DB30 owns real locked inputs and membership.

## 2. Join and field authority

`WWS_Code` is required, non-null, and unique in both target and source. Missing
or duplicate keys are fatal. The transform copies only:

- `PWS_ID`, `SrcName`, `PWS_Name`, `County_Nam`, `State`;
- `HUC10_ID`, `HUC10_Name`, `WWS_Code`, `SrcType`;
- `Shape_Leng`, `Shape_Area`, and `outlet_lon_lat`.

Target `WWS_Code` is the join authority and must equal the matched source value.
For every other approved field, an absent or null target accepts the source
value. An equal non-null target value passes; a different non-null target value
is a conflict and fails.

Unmatched unique target features remain in place, preserve target `WWS_Code`,
and receive the other approved fields as explicit null. Source-only features
are counted but never added. This produces separate matched, target-unmatched,
and source-unmatched counts without dropping or multiplying target members.

Fields absent from the approved WWS source—`OwnerType`, `PopGroup`,
`TreatType`, `ConnGroup`, and the `HUC10_*` utility aggregates—are not invented,
cleared, or changed by DB18.

## 3. Target preservation

The output is a deep copy of the target master with only the approved property
decisions above. Validation requires exact preservation of:

- feature count and order;
- every target run ID and its NASA 202606 prefix;
- geometry JSON for every feature; and
- every non-enrichment target property.

Historical source run IDs and source geometry are never copied. Successful
validation reports how many matched source run IDs and geometries differ from
their target authorities, along with total ignored counts. Mutation proof makes
run-ID, join-key, geometry, member-count, and other target-property changes
fatal.

## 4. Published provenance

A successful DB17 `prepare` run publishes and verifies:

1. the raw target and checksum-pinned enrichment inputs;
2. canonical enriched master GeoJSON;
3. a DB08 validation report;
4. DB08 transformation lineage; and
5. per-member metadata/boundary artifacts, exact member index, and source
   receipt.

The lineage fixes transformation key
`nasa-202606-wws-code-enrichment`, version `1.0.0`, join key `WWS_Code`,
configuration hash, two input references, output reference, fourteen unique
field decisions, matched/unmatched/duplicate counts, and validation-report
reference. Every member points to the same immutable lineage artifact.

Canonical serialization and the descriptor's fixed timestamp make the output,
report, lineage, member index, and receipt byte-identical when replayed from
DB12 objects. Receipt replay performs no upstream read.

## 5. Successor boundary

DB18's accepted evidence uses synthetic public fixtures only. It does not
claim the real target member count, real target checksum, current real-source
availability, production compatibility, or staging success.

DB30 must lock the real successor target, reviewed stable member mappings,
actual enrichment source, expected child artifacts, and real counts. DB20 and
DB21 then own deterministic materialization and isolated staging validation;
DB30A/DB31 own base adoption and production planning. Old NASA rows cannot be
removed merely because DB18 tooling exists.
