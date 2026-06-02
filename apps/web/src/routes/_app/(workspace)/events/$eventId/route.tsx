import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/(workspace)/events/$eventId')({
  component: EventRouteLayout,
})

function EventRouteLayout() {
  return <Outlet />
}
