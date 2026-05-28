import { createFileRoute } from '@tanstack/react-router'

import { EventsIndexPageContent } from '../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/events/')({
  component: EventsPage,
})

function EventsPage() {
  return <EventsIndexPageContent />
}
