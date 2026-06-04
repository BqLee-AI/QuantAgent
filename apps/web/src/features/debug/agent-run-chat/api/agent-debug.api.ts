import { BaseApi, type ApiClient } from '@/shared/api';

import type {
  AgentDebugApiContract,
  AgentDebugFixtureSummary,
  AgentDebugStreamOptions,
  AgentDebugSseEvent,
} from './agent-debug.contracts';
import { streamAgentDebugEvents } from './agent-debug.stream';

export class AgentDebugApi extends BaseApi implements AgentDebugApiContract {
  constructor(apiClient: ApiClient) {
    super(apiClient, { basePath: '/debug/agent-runs' });
  }

  listFixtures(): Promise<AgentDebugFixtureSummary[]> {
    return this.get<AgentDebugFixtureSummary[]>('/fixtures');
  }

  streamFixtureRun(options: AgentDebugStreamOptions): AsyncIterable<AgentDebugSseEvent> {
    return streamAgentDebugEvents({
      apiClient: this.apiClient,
      fixtureId: options.fixtureId,
      request: options.request,
      signal: options.signal,
    });
  }
}

export function createAgentDebugApi(apiClient: ApiClient): AgentDebugApi {
  return new AgentDebugApi(apiClient);
}
