import { createFileRoute, redirect } from "@tanstack/react-router";
import { fetchWatershed } from "../api/api";
import Home from "../pages/Home";

export const Route = createFileRoute("/watershed/$webcloudRunId")({
  beforeLoad: async ({ params }) => {
    let watershed;
    try {
      watershed = await fetchWatershed(params.webcloudRunId);
    } catch {
      return;
    }
    const watershedKey = watershed.properties.watershed_key;
    if (watershedKey) {
      throw redirect({
        to: "/watershed/key/$watershedKey",
        params: { watershedKey },
        replace: true,
      });
    }
  },
  component: Home,
});
