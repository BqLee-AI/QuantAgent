import { ApiError, type ApiClient } from '@/shared/api';

import type { AgentDebugRunRequest, AgentDebugSseEvent } from './agent-debug.contracts';
import { SseFrameParser } from '../utils/agent-run-sse-parser';

interface StreamFixtureRunOptions {
  apiClient: ApiClient;
  fixtureId: string;
  request: AgentDebugRunRequest;
  signal?: AbortSignal;
}

function parseEventData(data: string): AgentDebugSseEvent {
  const parsed = JSON.parse(data) as AgentDebugSseEvent;
  return parsed;
}

export async function* streamAgentDebugEvents({
  apiClient,
  fixtureId,
  request,
  signal,
}: StreamFixtureRunOptions): AsyncIterable<AgentDebugSseEvent> {
  const response = await apiClient.stream(`/debug/agent-runs/fixtures/${encodeURIComponent(fixtureId)}/stream`, {
    data: request,
    signal,
  });

  if (!response.body) {
    throw new ApiError({
      code: -2,
      msg: 'Agent debug stream response has no body.',
      status: response.status,
    });
  }

  const parser = new SseFrameParser();
  const decoder = new TextDecoder();

  for await (const chunk of response.body) {
    for (const frame of parser.push(decoder.decode(chunk, { stream: true }))) {
      if (!frame.data) continue;
      yield parseEventData(frame.data);
    }
  }

  for (const frame of parser.flush()) {
    if (!frame.data) continue;
    yield parseEventData(frame.data);
  }
}
