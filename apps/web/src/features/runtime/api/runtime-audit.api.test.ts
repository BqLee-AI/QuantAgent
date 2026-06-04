import { describe, expect, it, vi } from 'vitest';

import type { ApiClient } from '@/shared/api';

import { RuntimeAuditApi } from './runtime-audit.api';

function createApiClientMock(): ApiClient {
  return {
    del: vi.fn(),
    get: vi.fn(),
    instance: {} as ApiClient['instance'],
    patch: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    request: vi.fn(),
    requestEnvelope: vi.fn(),
    stream: vi.fn(),
  };
}

describe('RuntimeAuditApi', () => {
  it('requests backend news read model with query params', async () => {
    const client = createApiClientMock();
    vi.mocked(client.get).mockResolvedValue({ generated_at: 'now', items: [], next_cursor: null });
    const api = new RuntimeAuditApi(client);

    await api.listAuditNews({
      binding_id: 'binding-runtime-001',
      keyword: 'HBM',
      trace_id: 'trace-runtime-001',
    });

    expect(client.get).toHaveBeenCalledWith('/runtime/audit/news', {
      params: {
        binding_id: 'binding-runtime-001',
        keyword: 'HBM',
        trace_id: 'trace-runtime-001',
      },
    });
  });
});
