import { createFileRoute, redirect } from '@tanstack/react-router'

import { getDefaultWorkspaceEntry } from '../shared/auth'

export const Route = createFileRoute('/')({
  beforeLoad: ({ context }) => {
    if (context.auth?.status === 'unauthenticated') {
      throw redirect({ to: '/login' })
    }

    const defaultEntry = getDefaultWorkspaceEntry(context.capabilities)

    if (!defaultEntry) {
      throw redirect({ to: '/events' })
    }

    throw redirect({ to: defaultEntry })
  },
})
