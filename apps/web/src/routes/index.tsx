import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  beforeLoad: ({ context }) => {
    if (context.auth?.status !== 'authenticated') {
      throw redirect({
        search: { redirect: '/' },
        to: '/login',
      })
    }

    throw redirect({ to: '/events' })
  },
})
