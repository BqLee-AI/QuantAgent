import { createFileRoute } from '@tanstack/react-router'

import { EventDetailPage } from '../../../../../features/events'

export const Route = createFileRoute('/_app/(workspace)/events/$eventId/')({
  component: EventDetailRoutePage,
})

function EventDetailRoutePage() {
  const { eventId } = Route.useParams()

  return <EventDetailPage rawEventId={eventId} />
}
