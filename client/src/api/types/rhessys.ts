export type SpatialScale = "hillslope" | "patch";

export type RhessysSpatialLegendStop = {
  value: number;
  hex: string;
};

export type RhessysSpatialFile = {
  filename: string;
  name: string;
  type: "continuous" | "categorical" | "stream";
  min: number | null;
  max: number | null;
  unique_values: number[] | null;
  group: string | null;
  reversed: boolean;
  legend: RhessysSpatialLegendStop[] | null;
};

export type RhessysSpatialListResponse = {
  files: RhessysSpatialFile[];
};

export type RhessysOutputVariable = {
  id: string;
  label: string;
  units: string;
  filename?: string;
  spatial_scales?: SpatialScale[];
};

export type RhessysOutputScenario = {
  id: string;
  label: string;
  is_change: boolean;
  variables: string[];
  description?: string;
  year_range?: [number, number];
  geometry_revision?: string;
};

export type RhessysOutputValueRange = {
  min: number;
  max: number;
};

export type RhessysOutputListResponse = {
  scenarios: RhessysOutputScenario[];
  variables: RhessysOutputVariable[];
  value_ranges?: Record<string, Record<string, RhessysOutputValueRange>>;
  capability?: {
    available: boolean;
    source?: string;
    mode?: "dynamic" | "precomputed" | "both";
    supports_dynamic?: boolean;
    supports_precomputed?: boolean;
    index_uri?: string | null;
    index_sha256?: string | null;
    geometry_revision?: string | null;
    access_policy?: string | null;
  };
};

export type RhessysChoroplethRow = {
  spatialId: number;
  value: number;
};
