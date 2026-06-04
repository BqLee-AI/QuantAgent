import { ApiError, type ApiClient } from '@/shared/api';

import type { AgentDebugRunRequest, AgentDebugSseEvent } from './agent-debug.contracts';
import { SseFrameParser } from '../utils/agent-run-sse-parser';

interface StreamFixtureRunOptions {
  apiClient: ApiClient;
  fixtureId: string;
  request: AgentDebugRunRequest;
  signal?: AbortSignal;
}

function resolveStreamUrl(apiClient: ApiClient, path: string): string {
  const baseURL = String(apiClient.instance.defaults.baseURL ?? '/api/v1');
  if (/^https?:\/\//u.test(baseURL)) {
    return `${baseURL.replace(/\/+$/u, '')}${path}`;
  }
  return `${baseURL.replace(/\/+$/u, '')}${path}`;
}

function parseEventData(data: string): AgentDebugSseEvent {
  const parsed = JSON.parse(data) as AgentDebugSseEvent;
  return parsed;
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { msg?: string; request_id?: string; trace_id?: string; code?: number };
    return new ApiError({
      code: body.code ?? response.status,
      msg: body.msg ?? response.statusText,
      requestId: body.request_id,
      traceId: body.trace_id,
      status: response.status,
      cause: body,
    });
  } catch (error) {
    return new ApiError({
      code: response.status,
      msg: response.statusText || 'Agent debug stream failed.',
      status: response.status,
      cause: error,
    });
  }
}

export async function* streamAgentDebugEvents({
  apiClient,
  fixtureId,
  request,
  signal,
}: StreamFixtureRunOptions): AsyncIterable<AgentDebugSseEvent> {
  const url = resolveStreamUrl(apiClient, `/debug/agent-runs/fixtures/${encodeURIComponent(fixtureId)}/stream`);
  const headers = new Headers({ Accept: 'text/event-stream', 'Content-Type': 'application/json' });

  // 中文注释：SSE 必须读取 Response.body，axios 当前封装会先缓冲响应；fetch 仅封装在 feature API 层，组件和 hook 不直接接触底层协议。
  const response = await fetch(url, {
    body: JSON.stringify(request),
    credentials: apiClient.instance.defaults.withCredentials ? 'include' : 'same-origin',
    headers,
    method: 'POST',
    signal,
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

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
