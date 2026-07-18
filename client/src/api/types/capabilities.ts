export type CapabilitySummary = {
  available: boolean;
  source: "materialized" | "legacy-empty" | "none" | "invalid";
  mode: "dynamic" | "precomputed" | "both" | null;
  access_policy: "public" | "disabled" | null;
  index_uri: string | null;
  index_sha256: string | null;
  geometry_revision: string | null;
  scenarios: unknown[];
  variables: unknown[];
};

export type RuntimeCapabilitiesResponse = {
  state: "EMPTY" | "ACTIVE";
  rhessys: CapabilitySummary;
  sbs: CapabilitySummary;
};
