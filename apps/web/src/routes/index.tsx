import { createFileRoute, redirect } from '@tanstack/react-router'

import { PageLoading } from '../app/components/PageLoading'
import { getDefaultWorkspaceEntry } from '../shared/auth'

export const Route = createFileRoute('/')({
  beforeLoad: ({ context }) => {
    if (context.auth?.status === 'bootstrapping') {
      return
    }

    if (context.auth?.status === 'unauthenticated') {
      throw redirect({ to: '/login' })
    }

    const defaultEntry = getDefaultWorkspaceEntry(context.capabilities)

    if (!defaultEntry) {
      throw redirect({ to: '/events' })
    }

    throw redirect({ to: defaultEntry })
  },
  component: IndexRoute,
})

function IndexRoute() {
  return <PageLoading message="正在恢复登录状态..." />
}
