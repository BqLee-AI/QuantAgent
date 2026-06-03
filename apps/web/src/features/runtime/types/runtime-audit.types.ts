export type RuntimeAuditNewsStatus = 'captured' | 'linked' | 'pending' | 'routed' | 'unavailable';

export type RuntimeAuditNewsStage =
  | 'captured'
  | 'persisted'
  | 'scheduler_linked'
  | 'ai_intake_unavailable'
  | 'ai_intake_routed'
  | 'route_decided'
  | 'route_unavailable';

export type RuntimeAuditTimelineStatus = 'pending' | 'success' | 'unavailable' | 'warning';
export type RuntimeAuditAgentStageStatus = 'failed' | 'pending' | 'success' | 'unavailable';
export type RuntimeAuditAgentType = 'industry_main_agent' | 'router_agent';

export type RuntimeAuditSafeValue =
  | RuntimeAuditSafeValue[]
  | boolean
  | null
  | number
  | string
  | { [key: string]: RuntimeAuditSafeValue };

export interface RuntimeAuditNewsTrace {
  binding_id: string | null;
  correlation_id: string | null;
  raw_event_id: string;
  request_id: string | null;
  run_id: string | null;
  trace_id: string | null;
}

export interface RuntimeAuditNewsRef {
  id: string;
  kind: string;
  label: string;
}

export interface RuntimeAuditNewsTimelineStep {
  label: string;
  occurred_at: string | null;
  refs: RuntimeAuditNewsRef[];
  status: RuntimeAuditTimelineStatus;
  step_id: RuntimeAuditNewsStage;
  summary: string;
}

export interface RuntimeAuditAgentStage {
  agent_name: string;
  agent_type: RuntimeAuditAgentType;
  key_fields: Record<string, RuntimeAuditSafeValue>;
  output_json: Record<string, RuntimeAuditSafeValue> | null;
  refs: RuntimeAuditNewsRef[];
  stage_id: string;
  status: RuntimeAuditAgentStageStatus;
  summary: string;
  unavailable_reason: string | null;
}

export interface RuntimeAuditNewsItem {
  agent_stages: RuntimeAuditAgentStage[];
  author: string | null;
  canonical_url: string | null;
  content_preview: string | null;
  current_stage: RuntimeAuditNewsStage;
  first_captured_at: string;
  focus_stage: RuntimeAuditNewsStage;
  last_captured_at: string;
  published_at: string | null;
  raw_event_id: string;
  safe_details: Record<string, RuntimeAuditSafeValue>;
  source_name: string | null;
  source_plugin_id: string;
  status: RuntimeAuditNewsStatus;
  timeline: RuntimeAuditNewsTimelineStep[];
  title: string | null;
  trace: RuntimeAuditNewsTrace;
  url_host: string | null;
}

export interface RuntimeAuditNewsListResponse {
  generated_at: string;
  items: RuntimeAuditNewsItem[];
  next_cursor: string | null;
}

export interface RuntimeAuditFilters {
  binding_id: string;
  current_stage: RuntimeAuditNewsStage | 'all';
  keyword: string;
  request_id: string;
  source_plugin_id: string;
  status: RuntimeAuditNewsStatus | 'all';
  time_from: string;
  time_to: string;
  trace_id: string;
}

export interface RuntimeAuditQueryParams {
  binding_id?: string;
  current_stage?: RuntimeAuditNewsStage;
  cursor?: string;
  keyword?: string;
  limit?: number;
  request_id?: string;
  source_plugin_id?: string;
  status?: RuntimeAuditNewsStatus;
  time_from?: string;
  time_to?: string;
  trace_id?: string;
}

export interface RuntimeAuditHealthSummary {
  generated_at: string;
  label: string;
  partial_unavailable_count: number;
  status: 'degraded' | 'healthy' | 'unavailable';
  total_items: number;
}
