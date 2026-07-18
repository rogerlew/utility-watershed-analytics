import { API_ENDPOINTS } from "./apiEndpoints";
import { checkResponse } from "./errors";
import type { RuntimeCapabilitiesResponse } from "./types/capabilities";

export async function fetchCapabilities(
  runId: string,
  signal: AbortSignal,
): Promise<RuntimeCapabilitiesResponse> {
  const url = API_ENDPOINTS.CAPABILITIES(runId);
  const response = await fetch(url, { signal });
  return checkResponse<RuntimeCapabilitiesResponse>(response, {
    url,
    runId,
    prefix: "Runtime Capabilities",
  });
}
