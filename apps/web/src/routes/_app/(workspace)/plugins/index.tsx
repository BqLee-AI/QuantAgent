import { createFileRoute } from '@tanstack/react-router'

import { PluginsIndexPageContent } from '../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/plugins/')({
  component: PluginsPage,
})

function PluginsPage() {
  return <PluginsIndexPageContent />
}
