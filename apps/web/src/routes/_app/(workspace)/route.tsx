import { createFileRoute, Outlet, redirect, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'

import { ForbiddenPage } from '../../../app/components/ForbiddenPage'
import { PageLoading } from '../../../app/components/PageLoading'
import { MainLayout } from '../../../app/layouts/MainLayout'
import {
  canAccessWorkspaceRoute,
  getDefaultWorkspaceEntry,
  resolveWorkspaceRoutePath,
  type WorkspaceRoutePath,
  useAuth,
} from '../../../shared/auth'

export const Route = createFileRoute('/_app/(workspace)')({
  beforeLoad: ({ context, location }) => {
    if (context.auth?.status === 'unauthenticated') {
      const search = new URLSearchParams(location.search as Record<string, string>).toString()
      const redirectTarget = `${location.pathname}${search ? `?${search}` : ''}${location.hash}`

      throw redirect({
        search: {
          redirect: redirectTarget,
        },
        to: '/login',
      })
    }

    if (context.auth?.status === 'authenticated') {
      const pathname = location.pathname as string
      const guardedRoute = resolveWorkspaceRoutePath(pathname)

      if (!guardedRoute) {
        return
      }

      const result = canAccessWorkspaceRoute(
        context.capabilities,
        guardedRoute as WorkspaceRoutePath,
      )

      if (!result.allowed) {
        return {
          forbidden: true,
        }
      }
    }
  },
  component: AppRoute,
})

function AppRoute() {
  const auth = useAuth()
  const navigate = useNavigate()
  const routeContext = Route.useRouteContext()

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

  if ('forbidden' in routeContext && routeContext.forbidden) {
    return (
      <MainLayout>
        <ForbiddenPage
          details={auth.forbidden}
          onReturnToEntry={() => {
            const defaultEntry = getDefaultWorkspaceEntry(auth.capabilities) ?? '/'
            void navigate({ to: defaultEntry })
          }}
        />
      </MainLayout>
    )
  }

  return (
    <MainLayout>
      <Outlet />
    </MainLayout>
  )
}
