import { useQuery } from '@tanstack/react-query';

import { useAppRuntime } from '@/app/runtime';

import { createAgentDebugApi } from '../api';
import { agentDebugQueryKeys } from './agent-debug.keys';

export function useAgentDebugFixturesQuery() {
  const { apiClient } = useAppRuntime();
  const agentDebug = createAgentDebugApi(apiClient);

  return useQuery({
    queryFn: () => agentDebug.listFixtures(),
    queryKey: agentDebugQueryKeys.fixtures(),
  });
}
