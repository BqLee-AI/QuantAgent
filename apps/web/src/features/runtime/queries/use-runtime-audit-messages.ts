import { useQuery } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import type { RuntimeAuditQueryParams } from '../types';
import { runtimeAuditKeys } from './runtime-audit.keys';

export function useRuntimeAuditMessagesQuery(params: RuntimeAuditQueryParams) {
  const { runtimeAudit } = useApis();

  return useQuery({
    queryFn: () => runtimeAudit.listAuditMessages(params),
    queryKey: runtimeAuditKeys.messages(params),
  });
}
