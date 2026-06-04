import { describe, expect, it, vi } from 'vitest';

import type { ApiClient } from '@/shared/api';

import { streamAgentDebugEvents } from './agent-debug.stream';

function createResponseStream() {
  const encoder = new TextEncoder();
  let controllerRef: ReadableStreamDefaultController<Uint8Array> | null = null;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controllerRef = controller;
    },
  });

  return {
    close() {
      controllerRef?.close();
    },
    enqueue(value: string) {
      controllerRef?.enqueue(encoder.encode(value));
    },
    response: new Response(body, {
      headers: { 'content-type': 'text/event-stream' },
      status: 200,
    }),
  };
}

function frame(type: string, seq: number): string {
  return `event: ${type}\nid: evt-${seq}\ndata: ${JSON.stringify({
    agent_run_id: 'run-nvda',
    created_at: '2026-06-04T20:00:00Z',
    event_id: `evt-${seq}`,
    payload: {},
    safe_summary: `${type} summary`,
    seq,
    trace_id: 'trace-nvda',
    type,
  })}\n\n`;
}

describe('streamAgentDebugEvents', () => {
  it('yields events as chunks arrive before the response stream closes', async () => {
    const stream = createResponseStream();
    const apiClient = {
      stream: vi.fn(async () => stream.response),
    } as unknown as ApiClient;
    const iterator = streamAgentDebugEvents({
      apiClient,
      fixtureId: 'semiconductor-nvda-earnings',
      request: { scenario: 'primary' },
    })[Symbol.asyncIterator]();

    const first = iterator.next();
    stream.enqueue(frame('run.started', 1));

    await expect(first).resolves.toMatchObject({
      done: false,
      value: { seq: 1, type: 'run.started' },
    });

    const second = iterator.next();
    stream.enqueue(frame('tool.completed', 2));
    stream.close();

    await expect(second).resolves.toMatchObject({
      done: false,
      value: { seq: 2, type: 'tool.completed' },
    });
    await expect(iterator.next()).resolves.toMatchObject({ done: true });
    expect(apiClient.stream).toHaveBeenCalledWith(
      '/debug/agent-runs/fixtures/semiconductor-nvda-earnings/stream',
      expect.objectContaining({ data: { scenario: 'primary' } }),
    );
  });
});
