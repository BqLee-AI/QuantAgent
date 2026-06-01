import { createFileRoute } from '@tanstack/react-router'

import { RuntimeDashboardPageContent } from '../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/runtime/')({
  component: RuntimePage,
})

function RuntimePage() {
  return <RuntimeDashboardPageContent />
}
