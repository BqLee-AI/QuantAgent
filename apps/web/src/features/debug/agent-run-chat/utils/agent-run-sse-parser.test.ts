import { describe, expect, it } from 'vitest';

import { SseFrameParser, parseSseFrame } from './agent-run-sse-parser';

describe('SseFrameParser', () => {
  it('parses event, id and multiline data fields', () => {
    expect(parseSseFrame('event: run.started\nid: evt-1\ndata: {"a":1}\ndata: {"b":2}')).toEqual({
      data: '{"a":1}\n{"b":2}',
      event: 'run.started',
      id: 'evt-1',
    });
  });

  it('parses frames split across chunks', () => {
    const parser = new SseFrameParser();

    expect(parser.push('event: run.started\nid: evt-1\ndata: {"type":"run')).toEqual([]);
    expect(parser.push('.started"}\n\nevent: tool.completed\n')).toEqual([
      {
        data: '{"type":"run.started"}',
        event: 'run.started',
        id: 'evt-1',
      },
    ]);
    expect(parser.flush()).toEqual([
      {
        data: '',
        event: 'tool.completed',
      },
    ]);
  });
});
