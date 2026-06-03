import { describe, expect, it } from 'vitest';

import {
  toRuntimeAuditFilters,
  toRuntimeAuditQueryParams,
  toRuntimeAuditSearch,
} from './use-runtime-audit-filters';

describe('runtime audit filters', () => {
  it('maps URL search values to backend query params', () => {
    const filters = toRuntimeAuditFilters(toRuntimeAuditSearch({
      binding_id: 'binding-runtime-001',
      current_stage: 'scheduler_linked',
      keyword: 'HBM',
      request_id: 'req-runtime',
      source_plugin_id: 'quantagent.official.source.rss',
      status: 'linked',
      time_from: '2026-06-01T00:00:00Z',
      time_to: '2026-06-02T00:00:00Z',
      trace_id: 'trace-runtime',
    }));

    expect(toRuntimeAuditQueryParams(filters)).toEqual({
      binding_id: 'binding-runtime-001',
      current_stage: 'scheduler_linked',
      keyword: 'HBM',
      request_id: 'req-runtime',
      source_plugin_id: 'quantagent.official.source.rss',
      status: 'linked',
      time_from: '2026-06-01T00:00:00Z',
      time_to: '2026-06-02T00:00:00Z',
      trace_id: 'trace-runtime',
    });
  });

  it('drops all/empty values before requesting backend', () => {
    expect(toRuntimeAuditQueryParams(toRuntimeAuditFilters({
      binding_id: '  ',
      current_stage: 'all',
      status: 'all',
    }))).toEqual({});
  });

  it('keeps persisted routed status and route decision stage', () => {
    const filters = toRuntimeAuditFilters(toRuntimeAuditSearch({
      current_stage: 'route_decided',
      status: 'routed',
    }));

    expect(toRuntimeAuditQueryParams(filters)).toEqual({
      current_stage: 'route_decided',
      status: 'routed',
    });
  });
});
