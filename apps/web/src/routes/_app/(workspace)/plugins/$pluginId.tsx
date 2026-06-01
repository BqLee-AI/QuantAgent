import { createFileRoute } from '@tanstack/react-router'

import { PluginDetailPageContent } from '../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/plugins/$pluginId')({
  component: PluginDetailPage,
})

function PluginDetailPage() {
  const { pluginId } = Route.useParams()

  return <PluginDetailPageContent pluginId={pluginId} />
}
