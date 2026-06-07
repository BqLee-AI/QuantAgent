import { createFileRoute } from '@tanstack/react-router'

import { EventListPage } from '../../../../features/events'

export const Route = createFileRoute('/_app/(workspace)/events/')({
  component: EventsPage,
})

function EventsPage() {
  return <EventListPage />
}
