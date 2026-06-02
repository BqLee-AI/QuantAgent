import { createFileRoute } from '@tanstack/react-router'

import { EventAuditPage } from '@/features/event-audit'

export const Route = createFileRoute('/_app/(workspace)/events/$eventId/audit')({
  component: EventAuditRoutePage,
})

function EventAuditRoutePage() {
  const { eventId } = Route.useParams()

  return <EventAuditPage eventId={eventId} />
}
