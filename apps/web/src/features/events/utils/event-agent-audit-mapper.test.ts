import { describe, expect, it } from 'vitest';

import type { EventAgentStage, EventDetailResponse, EventRouterOutputResponse } from '../types';
import { toEventAgentAuditStages, toEventAgentAuditSubject } from './event-agent-audit-mapper';

describe('event agent audit mapper', () => {
  it('maps event detail into shared agent audit subject and stage without output by default', () => {
    const detail = createEventDetail();
    const subject = toEventAgentAuditSubject(detail);
    const [stage] = toEventAgentAuditStages(detail.agent_stages);

    expect(subject.subject_id).toBe('raw-1');
    expect(subject.title).toBe('先进封装产能扩张');
    expect(subject.trace?.routed_event_id).toBe('routed-1');
    expect(stage?.stage_kind).toBe('router_agent');
    expect(stage?.output_json).toBeNull();
    expect(stage?.key_fields.short_summary).toBe('先进封装产能扩张直接影响半导体后段供给。');
  });

  it('merges safe router output into selected stage only', () => {
    const detail = createEventDetail();
    const stages = toEventAgentAuditStages(detail.agent_stages, createRouterOutput());

    expect(stages[0]?.output_json?.schema_version).toBe('event_intake_decision.v2');
    expect(stages[0]?.output_json?.structured_news).toEqual(expect.objectContaining({
      canonical_title: '先进封装产能扩张',
    }));
  });
});

function createEventDetail(): EventDetailResponse {
  const routerStage: EventAgentStage = {
      agent_name: 'Router Agent',
      agent_type: 'router_agent',
      has_output_json: true,
      key_fields: {
        short_summary: '先进封装产能扩张直接影响半导体后段供给。',
      },
      refs: [{ id: 'routed-1', kind: 'routed_event', label: 'Routed Event' }],
      routed_event_id: 'routed-1',
      stage_id: 'router_agent',
      status: 'success',
      summary: 'Router Agent 已判断该新闻需要进入半导体行业分析。',
      unavailable_reason: null,
    };

  return {
    agent_stages: [routerStage],
    decision: 'route',
    discard_reason: null,
    event_type: 'capacity_expansion',
    priority: 'high',
    quality: {},
    raw_event_id: 'raw-1',
    relationship_summary: 'direct',
    router_stage_summary: routerStage,
    routed_at: '2026-06-05T00:00:00.000Z',
    routed_event_id: 'routed-1',
    safe_details: {},
    schema_version: 'event_intake_decision.v2',
    source_name: '示例媒体',
    source_plugin_id: 'quantagent.official.source.rss',
    status: 'success',
    summary: '先进封装产能扩张直接影响半导体后段供给。',
    tags: ['先进封装'],
    target_industries: ['industry:semiconductor'],
    target_topics: ['advanced-packaging'],
    timeline: [],
    title: '先进封装产能扩张',
    trace: {
      analysis_request_id: 'analysis-1',
      binding_id: 'binding-1',
      correlation_id: 'corr-1',
      raw_event_id: 'raw-1',
      request_id: 'req-1',
      routed_event_id: 'routed-1',
      source_message_id: 'message-1',
    },
    url: 'https://example.com/news',
    url_host: 'example.com',
    published_at: '2026-06-05T00:00:00.000Z',
  };
}

function createRouterOutput(): EventRouterOutputResponse {
  return {
    agent_stage: createEventDetail().agent_stages[0]!,
    output_json: {
      schema_version: 'event_intake_decision.v2',
      structured_news: {
        canonical_title: '先进封装产能扩张',
      },
    },
    raw_event_id: 'raw-1',
    routed_event_id: 'routed-1',
    schema_version: 'event_intake_decision.v2',
    trace: createEventDetail().trace,
  };
}
