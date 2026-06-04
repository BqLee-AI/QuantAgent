import { useQuery } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import { agentDebugQueryKeys } from './agent-debug.keys';

export function useAgentDebugFixturesQuery() {
  const { agentDebug } = useApis();

  return useQuery({
    queryFn: () => agentDebug.listFixtures(),
    queryKey: agentDebugQueryKeys.fixtures(),
  });
}
