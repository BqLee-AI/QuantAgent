export type AgentAuditStageKind =
  | 'industry_main_agent'
  | 'policy_gate'
  | 'router_agent'
  | 'tool_call'
  | 'unknown'
  | (string & {});

export type AgentAuditStageStatus =
  | 'failed'
  | 'masked'
  | 'pending'
  | 'skipped'
  | 'success'
  | 'unavailable'
  | 'warning'
  | (string & {});

export type AgentAuditSafeValue =
  | AgentAuditSafeValue[]
  | boolean
  | null
  | number
  | string
  | { [key: string]: AgentAuditSafeValue };

export interface AgentAuditTrace {
  binding_id?: string | null;
  correlation_id?: string | null;
  raw_event_id?: string | null;
  request_id?: string | null;
  routed_event_id?: string | null;
  run_id?: string | null;
  trace_id?: string | null;
}

export interface AgentAuditSubject {
  subject_id: string;
  title: string | null;
  url?: string | null;
  url_host?: string | null;
  source?: string | null;
  source_plugin_id?: string | null;
  published_at?: string | null;
  content_preview?: string | null;
  trace?: AgentAuditTrace;
}

export type AgentAuditKeyFieldState = 'masked' | 'normal' | 'unavailable';

export interface AgentAuditKeyField {
  label: string;
  value: AgentAuditSafeValue | undefined;
  description?: string;
  state?: AgentAuditKeyFieldState;
  unavailable_reason?: string | null;
}

export type AgentAuditKeyFields = Record<string, AgentAuditKeyField | AgentAuditSafeValue | undefined>;

export interface AgentAuditTraceRef {
  id: string;
  kind: string;
  label: string;
  href?: string | null;
}

export interface AgentAuditStage {
  stage_id: string;
  stage_kind: AgentAuditStageKind;
  status: AgentAuditStageStatus;
  title: string;
  summary: string;
  key_fields: AgentAuditKeyFields;
  output_json?: Record<string, AgentAuditSafeValue> | null;
  refs: AgentAuditTraceRef[];
  unavailable_reason?: string | null;
}
