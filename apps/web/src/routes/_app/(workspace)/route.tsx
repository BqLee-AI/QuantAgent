import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { PageLoading } from '../../../app/components/PageLoading'
import { MainLayout } from '../../../app/layouts/MainLayout'
import { useAuth } from '../../../shared/auth'

export const Route = createFileRoute('/_app/(workspace)')({
  beforeLoad: ({ context, location }) => {
    if (context.auth?.status === 'unauthenticated') {
      throw redirect({
        search: {
          redirect: location.pathname + location.search + location.hash,
        },
        to: '/login',
      })
    }
  },
  component: AppRoute,
})

function AppRoute() {
  const auth = useAuth()

  if (auth.status === 'bootstrapping') {
    return <PageLoading message="正在恢复登录状态..." />
  }

  return (
    <MainLayout>
      <Outlet />
    </MainLayout>
  )
}
