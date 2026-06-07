import { createFileRoute } from '@tanstack/react-router'

import { EventAuditPage } from '@/features/events'

export const Route = createFileRoute('/_app/(workspace)/events/$eventId/audit')({
  component: EventAuditRoutePage,
})

function EventAuditRoutePage() {
  const { eventId } = Route.useParams()

  return <EventAuditPage rawEventId={eventId} />
}
