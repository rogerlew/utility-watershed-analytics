import { queryOptions, keepPreviousData } from "@tanstack/react-query";
import { API_ENDPOINTS } from "./apiEndpoints";
import { checkResponse } from "./errors";
import { extractRows, toFiniteNumber } from "./utils";
import { queryKeys } from "./queryKeys";

import type {
  RhessysOutputListResponse,
  RhessysChoroplethRow,
  SpatialScale,
} from "./types/rhessys";

export type RhessysTimeSeriesRow = {
  year: number;
  month: number;
  day: number;
  [key: string]: number;
};

/**
 * Fetch the list of available RHESSys output map scenarios and variables.
 *
 * The backend probes the WEPPcloud file browser under `rhessys/maps/` and
 * returns the catalog of discovered scenario directories and variable TIFFs,
 * along with actual min/max value ranges for each scenario/variable combination.
 *
 * @param runId  - The `webcloud_run_id` of the watershed.
 * @param signal - {@link AbortSignal} for request cancellation.
 */
export async function fetchRhessysOutputs(
  runId: string,
  signal: AbortSignal,
): Promise<RhessysOutputListResponse> {
  const url = API_ENDPOINTS.RHESSYS_OUTPUTS_LIST(runId);
  const response = await fetch(url, { signal });
  return checkResponse<RhessysOutputListResponse>(response, {
    url,
    runId,
    prefix: "RHESSys Outputs",
  });
}

/**
 * Query the server-selected RHESSys dataset by semantic dimensions.
 *
 * Returns `{spatialId, value}` rows for choropleth rendering. Rows where
 * either field is non-finite are silently dropped.
 *
 * @param opts.runId        - The `webcloud_run_id` of the watershed.
 * @param opts.scenario     - RHESSys scenario id (e.g. `"S1"`).
 * @param opts.variable     - Column name to aggregate (e.g. `"streamflow"`).
 * @param opts.spatialScale - `"hillslope"` or `"patch"`.
 * @param opts.year         - Calendar year to filter on.
 * @param opts.signal       - {@link AbortSignal} for request cancellation.
 */
export async function fetchRhessysChoropleth(opts: {
  runId: string;
  scenario: string;
  variable: string;
  spatialScale: SpatialScale;
  year: number;
  signal: AbortSignal;
}): Promise<RhessysChoroplethRow[]> {
  const { runId, scenario, variable, spatialScale, year, signal } = opts;

  const url = API_ENDPOINTS.RHESSYS_QUERY(runId);
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind: "choropleth",
      scenario,
      variable,
      spatial_scale: spatialScale,
      year,
    }),
    signal,
  });

  type RawRow = { spatialId?: number; spatialid?: number; value?: number };
  const document = await checkResponse(response, {
    url,
    runId,
    prefix: "RHESSys Choropleth",
  });
  const rawRows = extractRows(document) as RawRow[];

  return rawRows
    .map((row) => ({
      spatialId: toFiniteNumber(row.spatialId ?? row.spatialid, NaN),
      value: toFiniteNumber(row.value, NaN),
    }))
    .filter((r) => Number.isFinite(r.spatialId) && Number.isFinite(r.value));
}

/**
 * Fetch the hillslope or patch GeoJSON geometry via the backend proxy.
 *
 * The backend selects the exact capability-declared geometry asset.
 *
 * @param runId        - The `webcloud_run_id` of the watershed.
 * @param spatialScale - `"hillslope"` or `"patch"`.
 * @param signal       - {@link AbortSignal} for request cancellation.
 * @param scenario     - Capability-declared scenario selecting the geometry revision.
 */
export async function fetchRhessysGeometry(
  runId: string,
  spatialScale: SpatialScale,
  signal: AbortSignal,
  scenario?: string | null,
): Promise<GeoJSON.FeatureCollection> {
  let url = API_ENDPOINTS.RHESSYS_OUTPUTS_GEOMETRY(runId, spatialScale);
  if (scenario) {
    url += `?scenario=${encodeURIComponent(scenario)}`;
  }

  const response = await fetch(url, { signal });
  return checkResponse<GeoJSON.FeatureCollection>(response, {
    url,
    runId,
    prefix: `RHESSys ${spatialScale} Geometry`,
  });
}

/**
 * Fetch a server-selected RHESSys time series by semantic dimensions.
 *
 * @param opts.runId        - The `webcloud_run_id` of the watershed.
 * @param opts.scenario     - RHESSys scenario id (e.g. `"S1"`).
 * @param opts.variables    - Column names to aggregate.
 * @param opts.spatialScale - `"hillslope"` or `"patch"`.
 * @param opts.signal       - {@link AbortSignal} for request cancellation.
 */
export async function fetchRhessysTimeSeries(opts: {
  runId: string;
  scenario: string;
  variables: string[];
  spatialScale?: SpatialScale | null;
  signal: AbortSignal;
}): Promise<RhessysTimeSeriesRow[]> {
  const { runId, scenario, variables, spatialScale, signal } = opts;
  const effectiveScale: SpatialScale = spatialScale ?? "hillslope";
  const isPatch = effectiveScale === "patch";
  const url = API_ENDPOINTS.RHESSYS_QUERY(runId);
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind: "time-series",
      scenario,
      variable: variables[0],
      spatial_scale: effectiveScale,
      year: null,
    }),
    signal,
  });
  const document = await checkResponse(response, {
    url,
    runId,
    prefix: "RHESSys TimeSeries",
  });
  const rawRows = extractRows(document);

  return rawRows.map((r) => {
    const row = r as Record<string, unknown>;
    const result: Record<string, number> = {
      year: toFiniteNumber(row.year, 0),
      month: isPatch ? 0 : toFiniteNumber(row.month, 1),
      day: 1,
    };
    for (const v of variables) {
      result[v] = toFiniteNumber(row[v], 0);
    }
    return result as RhessysTimeSeriesRow;
  });
}

type ChartPoint = { name: string; value: number };

type RhessysTimeSeriesParams = {
  runId: string | null;
  scenario: string;
  variable: string;
  spatialScale: SpatialScale;
};

export function rhessysTimeSeriesOptions({
  runId,
  scenario,
  variable,
  spatialScale,
}: RhessysTimeSeriesParams) {
  const isYearly = spatialScale === "patch";

  return queryOptions({
    queryKey: queryKeys.rhessysTimeSeries.byParams(
      runId ?? "",
      scenario,
      variable,
      spatialScale,
    ),
    queryFn: ({ signal }) =>
      fetchRhessysTimeSeries({
        runId: runId!,
        scenario,
        variables: [variable],
        spatialScale,
        signal,
      }),
    enabled: !!runId && !!scenario && !!variable,
    placeholderData: keepPreviousData,
    select: (rows: RhessysTimeSeriesRow[]): ChartPoint[] =>
      rows.map((row) => ({
        name: isYearly
          ? String(row.year)
          : `${row.year}-${String(row.month).padStart(2, "0")}`,
        value: (row[variable] as number) ?? 0,
      })),
  });
}
