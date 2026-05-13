import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/plugins/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('plugins:read')) throw redirect({ to: '/' })
  },
  component: PluginsPage,
})

/** Plugin management — lists installed source, industry, and executor plugins. */
function PluginsPage() {
  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900">Plugins</h1>
      <p className="mt-2 text-sm text-gray-500">Plugin management placeholder</p>
    </div>
  )
}
