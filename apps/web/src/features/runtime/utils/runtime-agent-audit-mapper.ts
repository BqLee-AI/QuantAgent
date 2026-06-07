import type { AgentAuditSafeValue, AgentAuditStage, AgentAuditSubject } from '@/features/agent-audit';

import type { RuntimeAuditAgentStage, RuntimeAuditNewsItem, RuntimeAuditNewsRef, RuntimeAuditSafeValue } from '../types';

export function toRuntimeAgentAuditSubject(item: RuntimeAuditNewsItem): AgentAuditSubject {
  return {
    content_preview: item.content_preview,
    published_at: item.published_at,
    source: item.source_name,
    source_plugin_id: item.source_plugin_id,
    subject_id: item.raw_event_id,
    title: item.title,
    trace: {
      binding_id: item.trace.binding_id,
      correlation_id: item.trace.correlation_id,
      raw_event_id: item.trace.raw_event_id,
      request_id: item.trace.request_id,
      run_id: item.trace.run_id,
      trace_id: item.trace.trace_id,
    },
    url: item.canonical_url,
    url_host: item.url_host,
  };
}

export function toRuntimeAgentAuditStages(stages: RuntimeAuditAgentStage[]): AgentAuditStage[] {
  return stages.map((stage) => ({
    key_fields: toAgentAuditSafeRecord(stage.key_fields),
    output_json: stage.output_json ? toAgentAuditSafeRecord(stage.output_json) : null,
    refs: stage.refs.map(toAgentAuditTraceRef),
    stage_id: stage.stage_id,
    stage_kind: stage.agent_type,
    status: stage.status,
    summary: stage.summary,
    title: stage.agent_name,
    unavailable_reason: stage.unavailable_reason,
  }));
}

function toAgentAuditTraceRef(ref: RuntimeAuditNewsRef) {
  return {
    id: ref.id,
    kind: ref.kind,
    label: ref.label,
  };
}

function toAgentAuditSafeRecord(value: Record<string, RuntimeAuditSafeValue>): Record<string, AgentAuditSafeValue> {
  const record: Record<string, AgentAuditSafeValue> = {};
  for (const [key, child] of Object.entries(value)) {
    record[key] = toAgentAuditSafeValue(child);
  }
  return record;
}

function toAgentAuditSafeValue(value: RuntimeAuditSafeValue): AgentAuditSafeValue {
  if (value === null || typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => toAgentAuditSafeValue(item));
  }
  return toAgentAuditSafeRecord(value);
}
