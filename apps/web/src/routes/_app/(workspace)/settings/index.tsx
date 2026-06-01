import { createFileRoute } from '@tanstack/react-router'

import { SettingsPageContent } from '../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/settings/')({
  component: SettingsPage,
})

function SettingsPage() {
  return <SettingsPageContent />
}
