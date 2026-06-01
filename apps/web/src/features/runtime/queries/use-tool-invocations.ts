import { useQuery } from "@tanstack/react-query";

import { useApis } from "@/app/runtime";

import type { RuntimeDashboardFilters } from "../types/runtime-dashboard.types";
import { toRuntimeListParams } from "../utils/runtime-query-params";
import { runtimeInspectKeys } from "./runtime-inspect.keys";

export function useToolInvocationsQuery(filters: RuntimeDashboardFilters) {
  const { runtimeInspect } = useApis();

  return useQuery({
    queryFn: () => runtimeInspect.listToolInvocations(toRuntimeListParams(filters)),
    queryKey: runtimeInspectKeys.toolInvocations(filters),
  });
}
