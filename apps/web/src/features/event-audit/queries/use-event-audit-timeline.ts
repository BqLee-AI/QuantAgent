import { useQuery } from '@tanstack/react-query'

import { useApis } from '@/app/runtime'

import { eventAuditKeys } from './event-audit.keys'

export function useEventAuditTimeline(eventId: string, options: { enabled?: boolean } = {}) {
  const { eventAudit } = useApis()

  return useQuery({
    enabled: options.enabled ?? true,
    queryFn: () => eventAudit.getEventAuditTimeline(eventId),
    queryKey: eventAuditKeys.timeline(eventId),
  })
}
