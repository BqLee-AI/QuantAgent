import { createRouter } from '@tanstack/react-router'

import { routeTree } from '../routeTree.gen'
import type { AuthState } from '../shared/auth'
import { debugRouteApi } from '@/debug/route-api.runtime'

export type RouterContext = {
  auth?: Pick<AuthState, 'capabilities' | 'status'>
  capabilities: Set<string>
}

export function createAppRouter() {
  const composedRouteTree = debugRouteApi.attachDebugRoutes(routeTree)

  return createRouter({
    routeTree: composedRouteTree,
    context: {
      capabilities: new Set<string>(),
    },
  })
}

export const router = createAppRouter()

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
