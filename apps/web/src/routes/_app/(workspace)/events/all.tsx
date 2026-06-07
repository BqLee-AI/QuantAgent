import { createFileRoute } from '@tanstack/react-router'

import { EventListPage } from '../../../../features/events'

export const Route = createFileRoute('/_app/(workspace)/events/all')({
  component: EventsAllPage,
})

function EventsAllPage() {
  return <EventListPage />
}
