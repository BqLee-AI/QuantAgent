import { createFileRoute, Outlet, redirect, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'

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
  const navigate = useNavigate()

  useEffect(() => {
    if (auth.status === 'unauthenticated') {
      void navigate({
        search: {
          redirect: window.location.pathname + window.location.search + window.location.hash,
        },
        to: '/login',
      })
    }
  }, [auth.status, navigate])

  if (auth.status === 'bootstrapping') {
    return <PageLoading message="正在恢复登录状态..." />
  }

  if (auth.status === 'unauthenticated') {
    return null
  }

  return (
    <MainLayout>
      <Outlet />
    </MainLayout>
  )
}
