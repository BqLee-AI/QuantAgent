import type { UseQueryResult } from "@tanstack/react-query";

import type {
  AgentRunSummary,
  RuntimeErrorSummary,
  RuntimeHealthSummary,
  RuntimeListResponse,
  SchedulerRunSummary,
  ToolInvocationSummary,
} from "../api";

export interface RuntimeDashboardFilters {
  event_id: string;
  page: number;
  page_size: number;
  plugin_id: string;
  status: string;
  time_from: string;
  time_to: string;
  trace_id: string;
}

export interface RuntimeDashboardFilterDraft {
  eventId: string;
  pluginId: string;
  status: string;
  timeFrom: string;
  timeTo: string;
  traceId: string;
}

export type RuntimeListQueryResult<TItem> = UseQueryResult<RuntimeListResponse<TItem>, Error>;

export interface RuntimeDashboardViewModel {
  agentRunsQuery: RuntimeListQueryResult<AgentRunSummary>;
  draft: RuntimeDashboardFilterDraft;
  filters: RuntimeDashboardFilters;
  healthQuery: UseQueryResult<RuntimeHealthSummary, Error>;
  isRefreshing: boolean;
  partialUnavailableCount: number;
  runtimeErrorsQuery: RuntimeListQueryResult<RuntimeErrorSummary>;
  schedulerRunsQuery: RuntimeListQueryResult<SchedulerRunSummary>;
  toolInvocationsQuery: RuntimeListQueryResult<ToolInvocationSummary>;
  updateDraft(nextDraft: Partial<RuntimeDashboardFilterDraft>): void;
  applyFilters(): void;
  resetFilters(): void;
  refreshAll(): void;
}
