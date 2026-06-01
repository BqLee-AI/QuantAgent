import { createFileRoute } from '@tanstack/react-router'

import { RuntimeAgentRunDetailPageContent } from '../../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/runtime/agents/$runId')({
  component: RuntimeAgentRunDetailPage,
})

function RuntimeAgentRunDetailPage() {
  const { runId } = Route.useParams()

  return <RuntimeAgentRunDetailPageContent runId={runId} />
}
