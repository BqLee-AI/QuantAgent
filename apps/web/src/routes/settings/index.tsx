import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/settings/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('settings:read')) throw redirect({ to: '/' })
  },
  component: SettingsPage,
})

function SettingsPage() {
  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900">Settings</h1>
      <p className="mt-2 text-sm text-gray-500">App settings placeholder</p>
    </div>
  )
}
