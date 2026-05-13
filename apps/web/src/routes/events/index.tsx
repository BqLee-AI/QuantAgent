import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/events/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('events:read')) throw redirect({ to: '/' })
  },
  component: EventsPage,
})

/** Events inbox page — lists incoming market events for review. */
function EventsPage() {
  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900">Events</h1>
      <p className="mt-2 text-sm text-gray-500">Event inbox placeholder</p>
    </div>
  )
}
