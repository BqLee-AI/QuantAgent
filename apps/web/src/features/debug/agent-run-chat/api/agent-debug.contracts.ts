export type AgentDebugScenario = 'primary' | 'media_follow_up';

export interface AgentDebugRunRequest {
  scenario: AgentDebugScenario;
}

export interface AgentDebugFixtureSummary {
  fixture_id: string;
  name: string;
  scenarios: AgentDebugScenario[];
  description: string;
}

export interface AgentDebugSseEvent {
  event_id: string;
  agent_run_id: string;
  type: AgentRunEventType;
  seq: number;
  created_at: string;
  payload: Record<string, unknown>;
  safe_summary: string | null;
  trace_id: string;
}

export type AgentRunEventType =
  | 'artifact.created'
  | 'model.delta'
  | 'run.completed'
  | 'run.failed'
  | 'run.output'
  | 'run.started'
  | 'subagent.completed'
  | 'subagent.started'
  | 'todo.updated'
  | 'tool.completed'
  | 'tool.failed'
  | 'tool.started';

export interface AgentDebugApiContract {
  listFixtures(): Promise<AgentDebugFixtureSummary[]>;
  streamFixtureRun(options: AgentDebugStreamOptions): AsyncIterable<AgentDebugSseEvent>;
}

export interface AgentDebugStreamOptions {
  fixtureId: string;
  request: AgentDebugRunRequest;
  signal?: AbortSignal;
}
