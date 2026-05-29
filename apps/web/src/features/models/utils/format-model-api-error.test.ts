import { describe, expect, it } from 'vitest';

import { ApiError } from '@/shared/api';

import { formatModelApiError } from './format-model-api-error';

describe('formatModelApiError', () => {
  it('returns null for non API errors', () => {
    expect(formatModelApiError(new Error('broken'))).toBeNull();
  });

  it('shows the safe API message without request id', () => {
    const error = new ApiError({ code: 40000, msg: '模型配置缺失' });

    expect(formatModelApiError(error)).toBe('模型配置缺失');
  });

  it('includes request id when available', () => {
    const error = new ApiError({
      code: 40000,
      msg: '模型配置缺失',
      requestId: 'req-model',
    });

    expect(formatModelApiError(error)).toBe('模型配置缺失（Request ID: req-model）');
  });
});
