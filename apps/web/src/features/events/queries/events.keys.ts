import { extendQueryKey } from '@/shared/query';

import type { EventQueryParams } from '../types';

export const eventKeys = {
  all: ['events'] as const,
  industryOptions: () => extendQueryKey(eventKeys.all, 'industry-options'),
  list: (params: EventQueryParams) => extendQueryKey(eventKeys.all, 'list', params),
  detail: (rawEventId: string) => extendQueryKey(eventKeys.all, 'detail', rawEventId),
  routerOutput: (rawEventId: string, routedEventId?: string | null) =>
    extendQueryKey(eventKeys.all, 'router-output', rawEventId, routedEventId ?? ''),
};
