export type BackendHealthStatus = "healthy" | "degraded" | "unavailable" | "not_configured";
export type RuntimeHealthSocketStatus = "connected" | "degraded" | "unknown";
export type RuntimeListResourceState = "ready" | "empty" | "unavailable";
export type RuntimePartialStatus = "ready" | "degraded" | "unavailable";

export interface RuntimeInspectListParams {
  page?: number;
  page_size?: number;
  event_id?: string | null;
  trace_id?: string | null;
  plugin_id?: string | null;
  status?: string | null;
  time_from?: string | null;
  time_to?: string | null;
}

export interface RuntimeErrorsListParams extends RuntimeInspectListParams {
  severity?: string | null;
  component?: string | null;
}

export interface SchedulerRunsListParams extends RuntimeInspectListParams {
  trigger_type?: string | null;
}

export interface RuntimeInspectPageInfo {
  page: number;
  page_size: number;
  returned: number;
  cursor?: string | null;
  next_cursor?: string | null;
}

export interface RuntimeInspectUnavailable {
  status: RuntimePartialStatus;
  reason: string;
  message: string;
}

export interface RuntimeListMeta {
  state: RuntimeListResourceState;
  page: RuntimeInspectPageInfo;
  unavailable: RuntimeInspectUnavailable | null;
}

export interface RuntimeListResponse<TItem> {
  items: TItem[];
  meta: RuntimeListMeta;
}

export interface RuntimeHealthSummary {
  active_agent_run_count: number;
  recent_failed_agent_run_count: number;
  recent_failed_tool_invocation_count: number;
  runtime_error_severity_summary: {
    critical: number;
    warning: number;
    info: number;
  };
  backend_status: {
    api: BackendHealthStatus;
    scheduler: BackendHealthStatus;
    worker: BackendHealthStatus;
  };
  websocket_status_hint: RuntimeHealthSocketStatus;
  partial_status: RuntimePartialStatus;
  unavailable_resources: RuntimeInspectUnavailable[];
  generated_at: string;
}

export interface RuntimeErrorSummaryPayload {
  error_code: string;
  error_message_summary: string;
  failure_stage?: string | null;
  retryable?: boolean | null;
}

export interface AgentRunSummary {
  run_id: string;
  event_id: string | null;
  trace_id: string | null;
  correlation_id: string | null;
  run_type: string;
  status: string;
  provider_policy: string | null;
  model_used: string | null;
  token_usage_summary: Record<string, unknown> | null;
  cost_estimate_summary: Record<string, unknown> | null;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  error_summary: RuntimeErrorSummaryPayload | null;
}

export interface ToolInvocationSummary {
  invocation_id: string;
  agent_run_id: string | null;
  event_id: string | null;
  trace_id: string | null;
  correlation_id: string | null;
  tool_id: string;
  plugin_id: string | null;
  risk_level: string | null;
  status: string;
  retry_count: number;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  error_summary: RuntimeErrorSummaryPayload | null;
}

export interface SchedulerRunSummary {
  run_id: string;
  binding_id: string | null;
  plugin_id: string | null;
  request_id: string | null;
  trigger_type: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
  error_summary: RuntimeErrorSummaryPayload | null;
}

export interface RuntimeErrorSummary {
  error_id: string;
  component: string;
  severity: string;
  status: string;
  error_code: string;
  error_message_summary: string;
  provider: string | null;
  provider_policy: string | null;
  trace_id: string | null;
  event_id: string | null;
  plugin_id: string | null;
  created_at: string;
}

export interface RuntimeInspectApiContract {
  getHealth(): Promise<RuntimeHealthSummary>;
  listAgentRuns(params?: RuntimeInspectListParams): Promise<RuntimeListResponse<AgentRunSummary>>;
  listToolInvocations(
    params?: RuntimeInspectListParams,
  ): Promise<RuntimeListResponse<ToolInvocationSummary>>;
  listSchedulerRuns(
    params?: SchedulerRunsListParams,
  ): Promise<RuntimeListResponse<SchedulerRunSummary>>;
  listRuntimeErrors(
    params?: RuntimeErrorsListParams,
  ): Promise<RuntimeListResponse<RuntimeErrorSummary>>;
}
