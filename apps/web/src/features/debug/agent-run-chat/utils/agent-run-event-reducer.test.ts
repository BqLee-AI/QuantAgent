import { describe, expect, it } from 'vitest';

import type { AgentDebugSseEvent } from '../api';
import { applyAgentRunEvent, createInitialAgentRunChatState } from './agent-run-event-reducer';

function event(overrides: Partial<AgentDebugSseEvent>): AgentDebugSseEvent {
  return {
    agent_run_id: 'run-nvda',
    created_at: '2026-06-04T20:00:00Z',
    event_id: overrides.event_id ?? `evt-${overrides.seq ?? 1}`,
    payload: {},
    safe_summary: null,
    seq: 1,
    trace_id: 'trace-nvda',
    type: 'run.started',
    ...overrides,
  };
}

describe('agent run event reducer', () => {
  it('maps core NVDA fixture events to structured display messages', () => {
    let state = createInitialAgentRunChatState();
    state = applyAgentRunEvent(state, event({ safe_summary: 'AgentRun started.', type: 'run.started' }));
    state = applyAgentRunEvent(state, event({
      event_id: 'evt-todo',
      payload: { todos: [{ content: 'Collect evidence', status: 'in_progress' }] },
      safe_summary: 'Todo updated.',
      seq: 2,
      type: 'todo.updated',
    }));
    state = applyAgentRunEvent(state, event({
      event_id: 'evt-tool',
      payload: { tool_name: 'search_web' },
      safe_summary: 'Public evidence search completed.',
      seq: 3,
      type: 'tool.completed',
    }));
    state = applyAgentRunEvent(state, event({
      event_id: 'evt-subagent',
      payload: { subagent_id: 'research', name: 'evidence_research_analyst' },
      safe_summary: 'EvidenceResearchAnalyst completed.',
      seq: 4,
      type: 'subagent.completed',
    }));
    state = applyAgentRunEvent(state, event({
      event_id: 'evt-artifact',
      payload: { artifact_id: 'artifact-analysis', kind: 'industry_analysis' },
      safe_summary: 'IndustryAnalysis: NVDA 一手财报支持小仓位 dry-run 做多计划。',
      seq: 5,
      type: 'artifact.created',
    }));
    state = applyAgentRunEvent(state, event({
      event_id: 'evt-output',
      payload: { trade_decision: 'submit_dry_run_open_long' },
      safe_summary: 'NVDA first-party earnings run produced dry-run action submission.',
      seq: 6,
      type: 'run.output',
    }));
    state = applyAgentRunEvent(state, event({ event_id: 'evt-done', safe_summary: 'AgentRun completed.', seq: 7, type: 'run.completed' }));

    expect(state.status).toBe('completed');
    expect(state.messages.map((message) => message.kind)).toEqual([
      'assistant',
      'todo',
      'tool',
      'subagent',
      'artifact',
      'final',
      'final',
    ]);
    expect(state.messages.find((message) => message.kind === 'tool')).toMatchObject({
      status: 'completed',
      toolName: 'search_web',
    });
    expect(state.messages.find((message) => message.kind === 'final')).toMatchObject({
      tradeDecision: 'submit_dry_run_open_long',
    });
  });

  it('redacts sensitive summaries before rendering', () => {
    const state = applyAgentRunEvent(createInitialAgentRunChatState(), event({
      safe_summary: 'secret prompt raw_response sk-test traceback',
      type: 'run.failed',
    }));

    expect(state.status).toBe('failed');
    expect(state.errorSummary).toBe('[已脱敏摘要]');
    expect(JSON.stringify(state.messages)).not.toContain('sk-test');
  });

  it('redacts sensitive payload strings before rendering display messages', () => {
    let state = createInitialAgentRunChatState();
    state = applyAgentRunEvent(state, event({
      event_id: 'evt-todo-sensitive',
      payload: { todos: [{ content: 'prompt raw_response sk-test-token', status: 'secret' }] },
      safe_summary: 'Todo updated.',
      seq: 2,
      type: 'todo.updated',
    }));
    state = applyAgentRunEvent(state, event({
      event_id: 'evt-tool-sensitive',
      payload: { tool_name: 'search_web sk-test-token' },
      safe_summary: 'Tool completed.',
      seq: 3,
      type: 'tool.completed',
    }));
    state = applyAgentRunEvent(state, event({
      event_id: 'evt-artifact-sensitive',
      payload: { artifact_id: 'artifact secret', kind: 'raw_response' },
      safe_summary: 'Artifact created.',
      seq: 4,
      type: 'artifact.created',
    }));
    state = applyAgentRunEvent(state, event({
      event_id: 'evt-output-sensitive',
      payload: { trade_decision: 'submit_dry_run_open_long traceback sk-test-token' },
      safe_summary: 'Run output.',
      seq: 5,
      type: 'run.output',
    }));

    const serialized = JSON.stringify(state.messages);
    expect(serialized).not.toContain('sk-test-token');
    expect(serialized).not.toContain('raw_response');
    expect(serialized).not.toContain('traceback');
    expect(serialized).toContain('[已脱敏摘要]');
  });
});
