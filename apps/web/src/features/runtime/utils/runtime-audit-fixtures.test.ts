import { describe, expect, it } from 'vitest';

import {
  createRuntimeAuditFixtureResponse,
  filterRuntimeAuditFixtureResponse,
} from './runtime-audit-fixtures';

describe('runtime audit fixtures', () => {
  it('covers RawEvent-backed captured, routed and AI unavailable examples', () => {
    const response = createRuntimeAuditFixtureResponse();

    expect(response.items).toHaveLength(2);
    expect(response.items.some((item) => item.status === 'routed')).toBe(true);
    expect(response.items.some((item) => item.current_stage === 'scheduler_linked')).toBe(true);
    expect(response.items.some((item) => item.timeline.some((step) => step.step_id === 'ai_intake_routed'))).toBe(true);
    expect(response.items.some((item) => item.timeline.some((step) => step.step_id === 'route_decided'))).toBe(true);
    expect(response.items.some((item) => item.timeline.some((step) => step.step_id === 'ai_intake_unavailable'))).toBe(true);
    expect(response.items.some((item) => item.timeline.some((step) => step.step_id === 'route_unavailable'))).toBe(true);
    expect(response.items.every((item) => item.agent_stages.some((stage) => stage.stage_id === 'router_agent'))).toBe(true);
    expect(response.items.every((item) => item.agent_stages.some((stage) => stage.stage_id === 'industry_main_agent'))).toBe(true);
  });

  it('contains a reusable Router Agent output fixture for detail modal tests', () => {
    const response = createRuntimeAuditFixtureResponse();
    const routerStage = response.items[0]?.agent_stages.find((stage) => stage.stage_id === 'router_agent');

    expect(routerStage?.status).toBe('success');
    expect(routerStage?.key_fields.short_summary).toBe('先进封装产能扩张直接影响半导体后段供给。');
    expect(routerStage?.output_json?.schema_version).toBe('event_intake_decision.v1');
    expect(routerStage?.output_json?.routing).toEqual(expect.objectContaining({
      target_topics: ['advanced-packaging', 'memory'],
    }));
  });

  it('filters news items by backend query params', () => {
    const response = filterRuntimeAuditFixtureResponse(
      createRuntimeAuditFixtureResponse(),
      {
        binding_id: 'binding-runtime-001',
        current_stage: 'scheduler_linked',
        keyword: 'HBM',
        request_id: 'req-capture-001',
        source_plugin_id: 'quantagent.official.source.rss',
        status: 'linked',
        time_from: '2026-06-01T00:00:00.000Z',
        time_to: '2026-06-01T23:59:59.000Z',
        trace_id: 'trace-runtime-001',
      },
    );

    expect(response.items).toHaveLength(1);
    expect(response.items[0]?.raw_event_id).toBe('rawevt-runtime-001');
  });

  it('ignores invalid time filter values instead of dropping all news items', () => {
    const response = filterRuntimeAuditFixtureResponse(
      createRuntimeAuditFixtureResponse(),
      { time_from: 'invalid-time' },
    );

    expect(response.items).toHaveLength(createRuntimeAuditFixtureResponse().items.length);
  });

  it('does not expose unsafe raw payload fixture details', () => {
    const response = createRuntimeAuditFixtureResponse();
    const serialized = JSON.stringify(response.items[0]?.safe_details);

    expect(serialized).not.toContain('must-redact');
    expect(response.items[0]?.safe_details.raw_payload).toEqual({ secret: '[已脱敏]' });
  });
});
