import { useQuery } from "@tanstack/react-query";

import { useApis } from "@/app/runtime";

import type { RuntimeDashboardFilters } from "../types/runtime-dashboard.types";
import { toRuntimeListParams } from "../utils/runtime-query-params";
import { runtimeInspectKeys } from "./runtime-inspect.keys";

export function useSchedulerRunsQuery(filters: RuntimeDashboardFilters) {
  const { runtimeInspect } = useApis();

  return useQuery({
    queryFn: () => runtimeInspect.listSchedulerRuns(toRuntimeListParams(filters)),
    queryKey: runtimeInspectKeys.schedulerRuns(filters),
  });
}
