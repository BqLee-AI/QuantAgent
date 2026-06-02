import { describe, expect, it } from 'vitest';

import {
  createRuntimeAuditFixtureResponse,
  filterRuntimeAuditFixtureResponse,
} from './runtime-audit-fixtures';

describe('runtime audit fixtures', () => {
  it('covers route, discard, review, degraded and schema-invalid examples', () => {
    const response = createRuntimeAuditFixtureResponse();

    expect(response.fixture_mode).toBe(true);
    expect(response.groups.some((group) => group.decision === 'route')).toBe(true);
    expect(response.groups.some((group) => group.decision === 'discard')).toBe(true);
    expect(response.groups.some((group) => group.decision === 'review')).toBe(true);
    expect(response.messages.some((message) => message.badges.includes('rss_summary_only'))).toBe(true);
    expect(response.messages.some((message) => message.badges.includes('schema_invalid'))).toBe(true);
    expect(response.health.partial_unavailable_count).toBeGreaterThan(0);
  });

  it('filters groups and messages by decision', () => {
    const response = filterRuntimeAuditFixtureResponse(
      createRuntimeAuditFixtureResponse(),
      { decision: 'discard' },
    );

    expect(response.groups).toHaveLength(1);
    expect(response.groups[0]?.decision).toBe('discard');
    expect(response.messages.every((message) => message.group_id === response.groups[0]?.group_id)).toBe(true);
  });

  it('filters groups and messages by status, industry, event, trace and time range', () => {
    const response = filterRuntimeAuditFixtureResponse(
      createRuntimeAuditFixtureResponse(),
      {
        event_id: 'EVT_CAPEX',
        industry: 'SEMICONDUCTOR',
        status: 'warning',
        time_from: '2026-06-03T00:00:00.000Z',
        time_to: '2026-06-03T01:00:00.000Z',
        trace_id: 'TRACE_REVIEW',
      },
    );

    expect(response.groups).toHaveLength(1);
    expect(response.groups[0]?.group_id).toBe('audit-router-review-capex');
    expect(response.messages.every((message) => message.group_id === 'audit-router-review-capex')).toBe(true);
  });

  it('ignores invalid time filter values instead of dropping all groups', () => {
    const response = filterRuntimeAuditFixtureResponse(
      createRuntimeAuditFixtureResponse(),
      { time_from: 'invalid-time' },
    );

    expect(response.groups).toHaveLength(createRuntimeAuditFixtureResponse().groups.length);
  });

  it('does not expose provider raw response in invalid fixture details', () => {
    const response = createRuntimeAuditFixtureResponse();
    const invalidMessage = response.messages.find((message) => message.id === 'msg-invalid-model');

    expect(invalidMessage?.safe_details?.provider_raw_response).toBe('[已脱敏]');
  });
});
