export type EventDecision = 'route' | 'review' | 'discard';
export type EventStatus = 'success' | 'failed';
export type EventSort = 'published_at_desc' | 'routed_at_desc';
export type EventTimelineStatus = 'success' | 'warning' | 'failed' | 'unavailable';
export type EventAgentStageStatus = 'success' | 'failed' | 'unavailable';
export type EventAgentType = 'router_agent' | 'industry_main_agent';

export interface EventTrace {
  raw_event_id: string;
  routed_event_id: string;
  binding_id: string | null;
  request_id: string | null;
  correlation_id: string | null;
  analysis_request_id: string | null;
  source_message_id: string | null;
}

export interface EventRef {
  kind: string;
  id: string;
  label: string;
}

export interface EventTimelineStep {
  step_id: string;
  label: string;
  status: EventTimelineStatus;
  occurred_at: string | null;
  summary: string;
  refs: EventRef[];
}

export interface EventAgentStage {
  stage_id: string;
  routed_event_id: string | null;
  agent_name: string;
  agent_type: EventAgentType;
  status: EventAgentStageStatus;
  summary: string;
  key_fields: Record<string, unknown>;
  refs: EventRef[];
  unavailable_reason: string | null;
  has_output_json: boolean;
}

export interface EventListItem {
  raw_event_id: string;
  routed_event_id: string;
  schema_version: string;
  title: string | null;
  url: string | null;
  url_host: string | null;
  source_name: string | null;
  source_plugin_id: string | null;
  published_at: string | null;
  routed_at: string;
  decision: EventDecision;
  discard_reason: string | null;
  status: EventStatus;
  summary: string | null;
  event_type: string | null;
  tags: string[];
  priority: string | null;
  relationship_summary: string | null;
  target_industries: string[];
  target_topics: string[];
  quality: Record<string, unknown>;
  trace: EventTrace;
  timeline: EventTimelineStep[];
  router_stage_summary: EventAgentStage;
}

export interface EventListResponse {
  items: EventListItem[];
  next_cursor: string | null;
  generated_at: string;
}

export interface EventDetailResponse extends EventListItem {
  safe_details: Record<string, unknown>;
  agent_stages: EventAgentStage[];
}

export interface EventRouterOutputResponse {
  raw_event_id: string;
  routed_event_id: string;
  schema_version: string;
  agent_stage: EventAgentStage;
  output_json: Record<string, unknown>;
  trace: EventTrace;
}

export interface EventQueryParams {
  keyword?: string;
  decision?: EventDecision | 'all';
  include_discard?: boolean;
  binding_id?: string;
  source_plugin_id?: string;
  industry_id?: string;
  target_topic?: string;
  priority?: string;
  relationship?: string;
  status?: EventStatus;
  trace_id?: string;
  request_id?: string;
  sort?: EventSort;
  time_from?: string;
  time_to?: string;
  cursor?: string;
  limit?: number;
}
