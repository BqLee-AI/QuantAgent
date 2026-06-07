import { useQuery } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import type { EventQueryParams } from '../types';
import { eventKeys } from './events.keys';

export function useEventListQuery(params: EventQueryParams) {
  const { events } = useApis();

  return useQuery({
    queryFn: () => events.listEvents(params),
    queryKey: eventKeys.list(params),
  });
}
