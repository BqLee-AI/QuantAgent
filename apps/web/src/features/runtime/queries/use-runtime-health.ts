import { useQuery } from "@tanstack/react-query";

import { useApis } from "@/app/runtime";

import { runtimeInspectKeys } from "./runtime-inspect.keys";

export function useRuntimeHealthQuery() {
  const { runtimeInspect } = useApis();

  return useQuery({
    queryFn: () => runtimeInspect.getHealth(),
    queryKey: runtimeInspectKeys.health(),
  });
}
