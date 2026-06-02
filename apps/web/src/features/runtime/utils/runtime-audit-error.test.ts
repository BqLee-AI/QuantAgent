import { describe, expect, it } from 'vitest';

import { ApiError } from '@/shared/api';

import {
  formatRuntimeAuditErrorMeta,
  isRuntimeAuditPermissionDenied,
} from './runtime-audit-error';

describe('runtime audit error helpers', () => {
  it('detects permission denied API errors', () => {
    const error = new ApiError({ code: 403, msg: 'forbidden', requestId: 'req-runtime' });

    expect(isRuntimeAuditPermissionDenied(error)).toBe(true);
  });

  it('formats request and trace metadata for audit states', () => {
    const error = new ApiError({
      code: 500,
      msg: 'failed',
      requestId: 'req-runtime',
      traceId: 'trace-runtime',
    });

    expect(formatRuntimeAuditErrorMeta(error)).toBe('request_id: req-runtime / trace_id: trace-runtime');
  });

  it('ignores non API errors', () => {
    expect(formatRuntimeAuditErrorMeta(new Error('failed'))).toBeNull();
    expect(isRuntimeAuditPermissionDenied(new Error('failed'))).toBe(false);
  });
});
