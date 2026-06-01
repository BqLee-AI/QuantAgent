import { useQuery } from "@tanstack/react-query";

import { useApis } from "@/app/runtime";

import type { RuntimeDashboardFilters } from "../types/runtime-dashboard.types";
import { toRuntimeListParams } from "../utils/runtime-query-params";
import { runtimeInspectKeys } from "./runtime-inspect.keys";

export function useAgentRunsQuery(filters: RuntimeDashboardFilters) {
  const { runtimeInspect } = useApis();

  return useQuery({
    queryFn: () => runtimeInspect.listAgentRuns(toRuntimeListParams(filters)),
    queryKey: runtimeInspectKeys.agentRuns(filters),
  });
}
