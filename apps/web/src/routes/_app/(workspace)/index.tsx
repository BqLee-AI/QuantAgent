import { createFileRoute } from '@tanstack/react-router'

import { DashboardPageContent } from '../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/')({
  component: DashboardPageContent,
})
