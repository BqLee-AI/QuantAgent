import { useQuery } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import { eventKeys } from './events.keys';

export function useEventDetailQuery(rawEventId: string) {
  const { events } = useApis();

  return useQuery({
    enabled: Boolean(rawEventId),
    queryFn: () => events.getEventDetail(rawEventId),
    queryKey: eventKeys.detail(rawEventId),
  });
}

export function useEventRouterOutputQuery(rawEventId: string, routedEventId?: string | null, enabled = false) {
  const { events } = useApis();

  return useQuery({
    enabled: enabled && Boolean(rawEventId),
    queryFn: () => events.getRouterOutput(rawEventId, routedEventId),
    queryKey: eventKeys.routerOutput(rawEventId, routedEventId),
  });
}
