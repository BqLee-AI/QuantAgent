import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/runtime/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('runtime:read')) throw redirect({ to: '/' })
  },
  component: RuntimePage,
})

function RuntimePage() {
  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900">Runtime</h1>
      <p className="mt-2 text-sm text-gray-500">Runtime dashboard placeholder</p>
    </div>
  )
}
