import { describe, expect, it } from 'vitest';

import { sanitizeAgentAuditJson } from './agent-audit-sanitize';

describe('sanitizeAgentAuditJson', () => {
  it('redacts unsafe agent audit keys recursively', () => {
    const sanitized = sanitizeAgentAuditJson({
      audit: {
        chain_of_thought: 'hidden reasoning',
        evidence_field_refs: ['structured_news.short_summary'],
      },
      provider_raw_response: 'raw model response',
      routing: {
        target_topics: ['hbm'],
        user_token: 'token-123',
      },
    });

    expect(sanitized).toEqual({
      audit: {
        chain_of_thought: '[已脱敏]',
        evidence_field_refs: ['structured_news.short_summary'],
      },
      provider_raw_response: '[已脱敏]',
      routing: {
        target_topics: ['hbm'],
        user_token: '[已脱敏]',
      },
    });
  });

  it('keeps safe structured output and handles unavailable payloads', () => {
    expect(sanitizeAgentAuditJson(null)).toBeNull();
    expect(sanitizeAgentAuditJson({
      decision: 'route',
      structured_news: {
        short_summary: 'HBM 供应链变化',
      },
    })).toEqual({
      decision: 'route',
      structured_news: {
        short_summary: 'HBM 供应链变化',
      },
    });
  });
});
