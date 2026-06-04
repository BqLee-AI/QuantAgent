import type { AgentDebugFixtureSummary, AgentDebugScenario } from '../api';

export type AgentRunChatStatus = 'aborted' | 'completed' | 'failed' | 'idle' | 'streaming';

export interface AgentRunTodoItem {
  content: string;
  status: string;
}

export type AgentRunChatMessage =
  | AgentRunArtifactMessage
  | AgentRunAssistantMessage
  | AgentRunErrorMessage
  | AgentRunFinalMessage
  | AgentRunSubagentMessage
  | AgentRunTodoMessage
  | AgentRunToolMessage;

export interface AgentRunBaseMessage {
  id: string;
  createdAt: string;
  seq: number;
  summary: string;
}

export interface AgentRunAssistantMessage extends AgentRunBaseMessage {
  kind: 'assistant';
  title: string;
}

export interface AgentRunTodoMessage extends AgentRunBaseMessage {
  kind: 'todo';
  todos: AgentRunTodoItem[];
}

export interface AgentRunToolMessage extends AgentRunBaseMessage {
  kind: 'tool';
  status: 'completed' | 'failed' | 'started';
  toolName: string;
}

export interface AgentRunSubagentMessage extends AgentRunBaseMessage {
  kind: 'subagent';
  status: 'completed' | 'started';
  subagentId: string | null;
  subagentName: string;
}

export interface AgentRunArtifactMessage extends AgentRunBaseMessage {
  artifactId: string;
  artifactKind: string;
  kind: 'artifact';
}

export interface AgentRunFinalMessage extends AgentRunBaseMessage {
  kind: 'final';
  title: string;
  tradeDecision: string | null;
}

export interface AgentRunErrorMessage extends AgentRunBaseMessage {
  kind: 'error';
}

export interface AgentRunChatState {
  agentRunId: string | null;
  currentScenario: AgentDebugScenario;
  errorSummary: string | null;
  lastTraceId: string | null;
  messages: AgentRunChatMessage[];
  status: AgentRunChatStatus;
}

export interface AgentRunChatPageModel {
  abortRun(): void;
  canStart: boolean;
  fixtures: readonly AgentDebugFixtureSummary[];
  fixturesError: string | null;
  isLoadingFixtures: boolean;
  selectedFixtureId: string;
  selectedScenario: AgentDebugScenario;
  setSelectedFixtureId(fixtureId: string): void;
  setSelectedScenario(scenario: AgentDebugScenario): void;
  startRun(): void;
  state: AgentRunChatState;
}
