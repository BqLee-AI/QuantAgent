import type { AgentDebugScenario, AgentDebugSseEvent } from '../api';
import type { AgentRunChatMessage, AgentRunChatState } from '../types';
import {
  formatEventTypeLabel,
  readStringPayload,
  readTodos,
  safeEventSummary,
} from './agent-run-event-format';

export function createInitialAgentRunChatState(scenario: AgentDebugScenario = 'primary'): AgentRunChatState {
  return {
    agentRunId: null,
    currentScenario: scenario,
    errorSummary: null,
    lastTraceId: null,
    messages: [],
    status: 'idle',
  };
}

export function markAgentRunAborted(state: AgentRunChatState): AgentRunChatState {
  if (state.status !== 'streaming') return state;
  return { ...state, status: 'aborted' };
}

export function applyAgentRunEvent(state: AgentRunChatState, event: AgentDebugSseEvent): AgentRunChatState {
  const base = {
    ...state,
    agentRunId: event.agent_run_id,
    lastTraceId: event.trace_id,
  };
  const nextMessage = toMessage(event);

  if (event.type === 'run.started') {
    return {
      ...base,
      errorSummary: null,
      messages: [nextMessage],
      status: 'streaming',
    };
  }

  if (event.type === 'run.completed') {
    return {
      ...base,
      messages: appendMessage(base.messages, nextMessage),
      status: 'completed',
    };
  }

  if (event.type === 'run.failed') {
    return {
      ...base,
      errorSummary: safeEventSummary(event),
      messages: appendMessage(base.messages, nextMessage),
      status: 'failed',
    };
  }

  return {
    ...base,
    messages: appendMessage(base.messages, nextMessage),
    status: base.status === 'idle' ? 'streaming' : base.status,
  };
}

function appendMessage(messages: AgentRunChatMessage[], message: AgentRunChatMessage): AgentRunChatMessage[] {
  return [...messages.filter((item) => item.id !== message.id), message].sort((a, b) => a.seq - b.seq);
}

function toMessage(event: AgentDebugSseEvent): AgentRunChatMessage {
  const base = {
    id: event.event_id,
    createdAt: event.created_at,
    seq: event.seq,
    summary: safeEventSummary(event),
  };

  if (event.type === 'todo.updated') {
    return {
      ...base,
      kind: 'todo',
      todos: readTodos(event),
    };
  }

  if (event.type === 'tool.started' || event.type === 'tool.completed' || event.type === 'tool.failed') {
    return {
      ...base,
      kind: 'tool',
      status: event.type === 'tool.failed' ? 'failed' : event.type === 'tool.completed' ? 'completed' : 'started',
      toolName: readStringPayload(event, 'tool_name') ?? 'unknown_tool',
    };
  }

  if (event.type === 'subagent.started' || event.type === 'subagent.completed') {
    return {
      ...base,
      kind: 'subagent',
      status: event.type === 'subagent.completed' ? 'completed' : 'started',
      subagentId: readStringPayload(event, 'subagent_id'),
      subagentName: readStringPayload(event, 'name') ?? readStringPayload(event, 'subagent_name') ?? 'SubAgent',
    };
  }

  if (event.type === 'artifact.created') {
    return {
      ...base,
      artifactId: readStringPayload(event, 'artifact_id') ?? 'unknown_artifact',
      artifactKind: readStringPayload(event, 'kind') ?? 'artifact',
      kind: 'artifact',
    };
  }

  if (event.type === 'run.output' || event.type === 'run.completed') {
    return {
      ...base,
      kind: 'final',
      title: formatEventTypeLabel(event.type),
      tradeDecision: readStringPayload(event, 'trade_decision'),
    };
  }

  if (event.type === 'run.failed') {
    return {
      ...base,
      kind: 'error',
    };
  }

  return {
    ...base,
    kind: 'assistant',
    title: formatEventTypeLabel(event.type),
  };
}
