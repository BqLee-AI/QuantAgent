import { createFileRoute } from '@tanstack/react-router'

import { ApprovalsIndexPageContent } from '../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/approvals/')({
  component: ApprovalsPage,
})

function ApprovalsPage() {
  return <ApprovalsIndexPageContent />
}
