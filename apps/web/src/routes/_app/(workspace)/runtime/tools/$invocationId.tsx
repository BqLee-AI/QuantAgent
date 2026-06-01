import { createFileRoute } from '@tanstack/react-router'

import { RuntimeToolInvocationDetailPageContent } from '../../../../../features/mainflow/MainflowSections'

export const Route = createFileRoute('/_app/(workspace)/runtime/tools/$invocationId')({
  component: RuntimeToolInvocationDetailPage,
})

function RuntimeToolInvocationDetailPage() {
  const { invocationId } = Route.useParams()

  return <RuntimeToolInvocationDetailPageContent invocationId={invocationId} />
}
