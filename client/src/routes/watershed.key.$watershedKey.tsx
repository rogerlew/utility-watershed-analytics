import { createFileRoute } from "@tanstack/react-router";
import { fetchWatershedByKey } from "../api/api";
import { RunIdContext } from "../contexts/RunIdContext";
import Home from "../pages/Home";

export const Route = createFileRoute("/watershed/key/$watershedKey")({
  loader: async ({ params }) => {
    const watershed = await fetchWatershedByKey(params.watershedKey);
    const currentRunId = watershed.properties.current_runid;
    if (!currentRunId) {
      throw new Error("Watershed has no current source run.");
    }
    return { currentRunId };
  },
  component: StableWatershedRoute,
});

function StableWatershedRoute() {
  const { currentRunId } = Route.useLoaderData();
  return (
    <RunIdContext.Provider value={currentRunId}>
      <Home />
    </RunIdContext.Provider>
  );
}
