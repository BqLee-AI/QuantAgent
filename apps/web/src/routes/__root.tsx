import {
  createRootRouteWithContext,
  Outlet,
  redirect,
  useNavigate,
  useRouterState,
} from '@tanstack/react-router'
import { useEffect } from 'react'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'

import { PageLoading } from '../app/components/PageLoading'
import { MainLayout } from '../app/layouts/MainLayout'
import type { RouterContext } from '../app/router'
import { useAuth } from '../shared/auth'

export const Route = createRootRouteWithContext<RouterContext>()({
  beforeLoad: ({ context, location }) => {
    const isLoginRoute = location.pathname === '/login'
    const isAuthenticated = context.auth?.status === 'authenticated'

    if (
      !isLoginRoute &&
      context.auth?.status === 'unauthenticated' &&
      !isAuthenticated
    ) {
      throw redirect({
        search: {
          redirect: location.href,
        },
        to: '/login',
      })
    }

    return {
      redirectToLogin: false,
    }
  },
  component: RootRoute,
})

function RootRoute() {
  const auth = useAuth()
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (state) => state.location.pathname })
  const isLoginRoute = pathname === '/login'

  useEffect(() => {
    if (!isLoginRoute && auth.status === 'unauthenticated') {
      void navigate({
        search: {
          redirect: pathname,
        },
        to: '/login',
      })
    }
  }, [auth.status, isLoginRoute, navigate, pathname])

  if (auth.status === 'bootstrapping') {
    return <PageLoading message="Restoring session..." />
  }

  return (
    <>
      {isLoginRoute ? <Outlet /> : <MainLayout />}
      {import.meta.env.DEV ? <TanStackRouterDevtools /> : null}
    </>
  )
}
