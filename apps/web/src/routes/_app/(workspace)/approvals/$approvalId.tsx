import { createFileRoute } from '@tanstack/react-router'

import { ApprovalDetailPageContent } from '../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/approvals/$approvalId')({
  component: ApprovalDetailPage,
})

function ApprovalDetailPage() {
  const { approvalId } = Route.useParams()

  return <ApprovalDetailPageContent approvalId={approvalId} />
}
