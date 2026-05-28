import { createFileRoute } from '@tanstack/react-router'

import { EventAuditPageContent } from '../../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/events/$eventId/audit')({
  component: EventAuditPage,
})

function EventAuditPage() {
  const { eventId } = Route.useParams()

  return <EventAuditPageContent eventId={eventId} />
}
