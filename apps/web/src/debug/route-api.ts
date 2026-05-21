import type { AnyRoute } from '@tanstack/react-router'

export type DebugRouteApi = {
  attachDebugRoutes: (routeTree: AnyRoute) => AnyRoute
}

export function createNoopDebugRouteApi(): DebugRouteApi {
  return {
    attachDebugRoutes: (routeTree) => routeTree,
  }
}
