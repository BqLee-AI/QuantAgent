export type RuntimeAuditDecision = 'discard' | 'review' | 'route';

export type RuntimeAuditStatus = 'error' | 'pending' | 'success' | 'unavailable' | 'warning';

export type RuntimeAuditStage =
  | 'analysis_requested'
  | 'context_built'
  | 'decision_validated'
  | 'discarded'
  | 'event_routed_published'
  | 'failed'
  | 'model_invoked'
  | 'review_requested';

export type RuntimeAuditActorType = 'agent' | 'event_bus' | 'model' | 'source' | 'system' | 'worker';

export type RuntimeAuditPriority = 'high' | 'low' | 'normal' | 'urgent';

export type RuntimeAuditBadge =
  | 'degraded'
  | 'partial_unavailable'
  | 'provider_failed'
  | 'rss_summary_only'
  | 'schema_invalid';

export type RuntimeAuditRelatedRefKind =
  | 'agent_run'
  | 'event_topic'
  | 'runtime_error'
  | 'scheduler_run'
  | 'tool_invocation';

export interface RuntimeAuditTrace {
  analysis_request_id?: string;
  binding_id?: string;
  correlation_id?: string;
  event_id?: string;
  raw_event_id?: string;
  request_id?: string;
  routed_event_id?: string;
  source_message_id?: string;
  trace_id?: string;
}

export interface RuntimeAuditEvidenceRef {
  field_path: string;
  label: string;
}

export interface RuntimeAuditRelatedRef {
  id: string;
  kind: RuntimeAuditRelatedRefKind;
  label: string;
}

export type RuntimeAuditSafeValue =
  | RuntimeAuditSafeValue[]
  | boolean
  | null
  | number
  | string
  | { [key: string]: RuntimeAuditSafeValue };

export interface RuntimeAuditMessage {
  actor_type: RuntimeAuditActorType;
  badges: RuntimeAuditBadge[];
  decision?: RuntimeAuditDecision;
  evidence_refs: RuntimeAuditEvidenceRef[];
  group_id: string;
  id: string;
  occurred_at: string | null;
  priority?: RuntimeAuditPriority;
  related_refs: RuntimeAuditRelatedRef[];
  safe_details: Record<string, RuntimeAuditSafeValue> | null;
  stage: RuntimeAuditStage;
  status: RuntimeAuditStatus;
  summary: string;
  title: string;
  trace: RuntimeAuditTrace;
}

export interface RuntimeAuditMessageGroup {
  decision?: RuntimeAuditDecision;
  group_id: string;
  industry: string;
  message_ids: string[];
  occurred_at: string | null;
  source_title: string;
  status: RuntimeAuditStatus;
  summary: string;
  trace: RuntimeAuditTrace;
}

export interface RuntimeAuditHealthSummary {
  generated_at: string;
  label: string;
  partial_unavailable_count: number;
  status: 'degraded' | 'healthy' | 'unavailable';
  total_groups: number;
}

export interface RuntimeAuditFilters {
  decision: RuntimeAuditDecision | 'all';
  event_id: string;
  industry: string;
  status: RuntimeAuditStatus | 'all';
  time_from: string;
  time_to: string;
  trace_id: string;
}

export interface RuntimeAuditQueryParams {
  decision?: RuntimeAuditDecision;
  event_id?: string;
  industry?: string;
  status?: RuntimeAuditStatus;
  time_from?: string;
  time_to?: string;
  trace_id?: string;
}

export interface RuntimeAuditMessagesResponse {
  fixture_mode: boolean;
  generated_at: string;
  groups: RuntimeAuditMessageGroup[];
  health: RuntimeAuditHealthSummary;
  messages: RuntimeAuditMessage[];
}
