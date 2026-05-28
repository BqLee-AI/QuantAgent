import { createFileRoute } from '@tanstack/react-router'

import { ApprovalLinkPageContent } from '../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/(public)/approval-link/$token')({
  component: ApprovalLinkPage,
})

function ApprovalLinkPage() {
  const { token } = Route.useParams()

  return <ApprovalLinkPageContent token={token} />
}
