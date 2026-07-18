import { useQuery } from "@tanstack/react-query";
import { fetchCapabilities } from "../api/capabilitiesApi";
import { queryKeys } from "../api/queryKeys";

export function useCapabilities(runId: string | null) {
  return useQuery({
    queryKey: queryKeys.capabilities.byRun(runId ?? ""),
    queryFn: ({ signal }) => fetchCapabilities(runId!, signal),
    enabled: !!runId,
  });
}
