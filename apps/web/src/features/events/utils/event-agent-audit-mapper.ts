import type { AgentAuditSafeValue, AgentAuditStage, AgentAuditSubject } from '@/features/agent-audit';

import type { EventAgentStage, EventDetailResponse, EventListItem, EventRef, EventRouterOutputResponse } from '../types';

export function toEventAgentAuditSubject(event: EventDetailResponse | EventListItem): AgentAuditSubject {
  return {
    content_preview: event.summary,
    published_at: event.published_at,
    source: event.source_name,
    source_plugin_id: event.source_plugin_id,
    subject_id: event.raw_event_id,
    title: event.title,
    trace: {
      binding_id: event.trace.binding_id,
      correlation_id: event.trace.correlation_id,
      raw_event_id: event.trace.raw_event_id,
      request_id: event.trace.request_id,
      routed_event_id: event.trace.routed_event_id,
    },
    url: event.url,
    url_host: event.url_host,
  };
}

export function toEventAgentAuditStage(stage: EventAgentStage, output?: EventRouterOutputResponse | null): AgentAuditStage {
  return {
    key_fields: toAgentAuditSafeRecord(stage.key_fields),
    output_json: output ? toAgentAuditSafeRecord(output.output_json) : null,
    refs: stage.refs.map(toAgentAuditTraceRef),
    stage_id: stage.stage_id,
    stage_kind: stage.agent_type,
    status: stage.status,
    summary: stage.summary,
    title: stage.agent_name,
    unavailable_reason: output?.agent_stage.unavailable_reason ?? stage.unavailable_reason,
  };
}

export function toEventAgentAuditStages(
  stages: EventAgentStage[],
  selectedOutput?: EventRouterOutputResponse | null,
): AgentAuditStage[] {
  return stages.map((stage) =>
    toEventAgentAuditStage(stage, selectedOutput?.agent_stage.stage_id === stage.stage_id ? selectedOutput : null),
  );
}

function toAgentAuditTraceRef(ref: EventRef) {
  return {
    id: ref.id,
    kind: ref.kind,
    label: ref.label,
  };
}

export function toAgentAuditSafeRecord(value: Record<string, unknown>): Record<string, AgentAuditSafeValue> {
  const record: Record<string, AgentAuditSafeValue> = {};
  for (const [key, child] of Object.entries(value)) {
    record[key] = toAgentAuditSafeValue(child);
  }
  return record;
}

function toAgentAuditSafeValue(value: unknown): AgentAuditSafeValue {
  if (value === null || typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => toAgentAuditSafeValue(item));
  }
  if (typeof value === 'object') {
    return toAgentAuditSafeRecord(value as Record<string, unknown>);
  }
  return String(value);
}
