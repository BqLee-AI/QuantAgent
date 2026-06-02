import { extendQueryKey, queryRootKeys } from '@/shared/query';

import type { RuntimeAuditQueryParams } from '../types';

export const runtimeAuditKeys = {
  all: queryRootKeys.runtime,
  audit: () => extendQueryKey(runtimeAuditKeys.all, 'audit'),
  messages: (params: RuntimeAuditQueryParams) =>
    extendQueryKey(runtimeAuditKeys.audit(), 'messages', params),
};
