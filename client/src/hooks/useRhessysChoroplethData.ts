import { useMemo } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useRunId } from "./useRunId";
import { queryKeys } from "../api/queryKeys";
import { useWatershed } from "../contexts/WatershedContext";
import { getLayerParams } from "../layers/types";
import { computeRobustRange } from "../utils/colormap";

import {
  fetchRhessysChoropleth,
  fetchRhessysGeometry,
} from "../api/rhessysOutputsApi";
import { useRhessysOutputsData } from "./useRhessysOutputsData";

export function useRhessysChoroplethData() {
  const runId = useRunId();

  const { layerDesired, isEffective } = useWatershed();
  const params = getLayerParams(layerDesired, "rhessysOutputs");
  const isActive =
    isEffective("rhessysOutputs") && params.mode === "choropleth";

  const scenario = params.scenario;
  const variable = params.variable;
  const spatialScale = params.spatialScale ?? "hillslope";
  const year = params.year;
  const { scenarios } = useRhessysOutputsData(runId);

  const shouldQuery = isActive && !!runId && !!scenario && !!variable && !!year;

  const { data: rawData, isLoading: dataLoading } = useQuery({
    queryKey: queryKeys.rhessysChoropleth.byParams(
      runId ?? "",
      scenario!,
      variable!,
      spatialScale,
      year!,
    ),
    queryFn: ({ signal }) =>
      fetchRhessysChoropleth({
        runId: runId!,
        scenario: scenario!,
        variable: variable!,
        spatialScale,
        year: year!,
        signal,
      }),
    enabled: shouldQuery,
    placeholderData: keepPreviousData,
  });

  const geometryRevision =
    scenarios.find((item) => item.id === scenario)?.geometry_revision ?? null;

  const { data: geometry, isLoading: geomLoading } = useQuery({
    queryKey: queryKeys.rhessysGeometry.byScale(
      runId ?? "",
      spatialScale,
      geometryRevision,
    ),
    queryFn: ({ signal }) =>
      fetchRhessysGeometry(runId!, spatialScale, signal, scenario),
    enabled: isActive && !!runId && !!scenario && !!geometryRevision,
    placeholderData: keepPreviousData,
  });

  const isLoading = dataLoading || geomLoading;

  const range = useMemo(() => {
    if (!rawData || rawData.length === 0) return null;
    const values = rawData.map((row) => row.value);
    return computeRobustRange(values, 0.0, 1.0);
  }, [rawData]);

  return {
    isActive,
    isLoading,
    rawData: rawData ?? null,
    geometry: geometry ?? null,
    range,
    spatialScale,
  };
}
