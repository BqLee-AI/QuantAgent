import { createFileRoute } from '@tanstack/react-router'

import { EventDetailPageContent } from '../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/events/$eventId')({
  component: EventDetailPage,
})

function EventDetailPage() {
  const { eventId } = Route.useParams()

  return <EventDetailPageContent eventId={eventId} />
}
