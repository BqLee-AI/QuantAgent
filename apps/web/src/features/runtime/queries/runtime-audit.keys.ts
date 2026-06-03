import { extendQueryKey, queryRootKeys } from '@/shared/query';

import type { RuntimeAuditQueryParams } from '../types';

export const runtimeAuditKeys = {
  all: queryRootKeys.runtime,
  audit: () => extendQueryKey(runtimeAuditKeys.all, 'audit'),
  news: (params: RuntimeAuditQueryParams) =>
    extendQueryKey(runtimeAuditKeys.audit(), 'news', params),
};
