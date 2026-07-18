import { useContext } from "react";
import { useParams } from "@tanstack/react-router";
import { RunIdContext } from "../contexts/RunIdContext";

export function useRunId(): string | null {
  const contextualRunId = useContext(RunIdContext);
  const routeRunId = useParams({
    from: "/watershed/$webcloudRunId",
    select: (params) => params?.webcloudRunId,
    shouldThrow: false,
  });
  return contextualRunId ?? routeRunId ?? null;
}
