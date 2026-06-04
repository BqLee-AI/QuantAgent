import { createRoute } from '@tanstack/react-router'
import type { AnyRoute } from '@tanstack/react-router'

import {
  AgentRunChatPage,
} from '@/features/debug/agent-run-chat'
import {
  DebugErrorFallbackIndexPage,
  DebugErrorFallbackThrowPage,
  DebugPageStatesPage,
  DebugPluginConfigFormPage,
  DebugRoutePlaygroundPage,
  DebugRuntimeConfigPage,
  DebugWorkbenchIndexPage,
  DebugWorkbenchPage,
} from '../workbench/DebugPages'
import {
  isDebugPageRouteKey,
  isDebugPageState,
  isDebugRoutePreview,
} from '../workbench/debugRouteModel'
import type {
  DebugPageStatesSearch,
  DebugRoutePlaygroundSearch,
} from '../workbench/debugRouteTypes'
import type { DebugRouteApi } from './route-api'

function getRouteOptions(route: AnyRoute | null | undefined): {
  id?: string
  path?: string
} {
  return (route?.options ?? {}) as { id?: string; path?: string }
}

function getRouteId(route: AnyRoute | null | undefined): string | undefined {
  return route?.id || getRouteOptions(route).id
}

function getRoutePath(route: AnyRoute | null | undefined): string | undefined {
  return route?.fullPath || route?.path || getRouteOptions(route).path
}

function getRouteChildren(route: AnyRoute | null | undefined): AnyRoute[] {
  const children = route?.children
  if (Array.isArray(children)) {
    return children
  }
  if (children && typeof children === 'object') {
    return Object.values(children) as AnyRoute[]
  }
  return []
}

export const debugRouteApi: DebugRouteApi = {
  attachDebugRoutes: (routeTree) => {
    const rootChildren = getRouteChildren(routeTree)
    const workspaceRoute =
      rootChildren.find((child) => getRouteId(child) === '/_app/(workspace)') ?? null

    if (!workspaceRoute) {
      throw new Error('未找到 /_app/(workspace) layout route，无法挂载开发态 /debug 工作台。')
    }

    const workspaceChildren = getRouteChildren(workspaceRoute)

    if (
      workspaceChildren.some(
        (child: AnyRoute) => getRouteId(child) === '/_app/(workspace)/debug' || getRoutePath(child) === '/debug',
      )
    ) {
      return routeTree
    }

    const debugRoute = createRoute({
      getParentRoute: () => workspaceRoute,
      path: '/debug',
      component: DebugWorkbenchPage,
    })

    const debugIndexRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: '/',
      component: DebugWorkbenchIndexPage,
    })

    const debugPageStatesRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'page-states',
      validateSearch: (search): DebugPageStatesSearch => ({
        route: isDebugPageRouteKey(search.route) ? search.route : 'events',
        state: isDebugPageState(search.state) ? search.state : 'overview',
      }),
      component: () => {
        const search = debugPageStatesRoute.useSearch()
        return <DebugPageStatesPage route={search.route ?? 'events'} state={search.state ?? 'overview'} />
      },
    })

    const debugRuntimeConfigRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'runtime-config',
      component: DebugRuntimeConfigPage,
    })

    const debugErrorFallbackRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'error-fallback',
      component: DebugErrorFallbackIndexPage,
    })

    const debugErrorFallbackThrowRoute = createRoute({
      getParentRoute: () => debugErrorFallbackRoute,
      path: 'throw',
      component: DebugErrorFallbackThrowPage,
    })

    const debugRoutePlaygroundRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'route-playground',
      validateSearch: (search): DebugRoutePlaygroundSearch => ({
        preview: isDebugRoutePreview(search.preview) ? search.preview : undefined,
      }),
      component: () => {
        const search = debugRoutePlaygroundRoute.useSearch()
        return <DebugRoutePlaygroundPage preview={search.preview} />
      },
    })

    const debugPluginConfigFormRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'plugin-config-form',
      component: DebugPluginConfigFormPage,
    })

    const debugAgentRunChatRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'agent-run-chat',
      component: AgentRunChatPage,
    })

    const debugErrorFallbackRouteTree = debugErrorFallbackRoute.addChildren([debugErrorFallbackThrowRoute])
    const debugRouteTree = debugRoute.addChildren([
      debugIndexRoute,
      debugPageStatesRoute,
      debugRuntimeConfigRoute,
      debugErrorFallbackRouteTree,
      debugRoutePlaygroundRoute,
      debugPluginConfigFormRoute,
      debugAgentRunChatRoute,
    ])

    workspaceRoute.addChildren([...workspaceChildren, debugRouteTree])
    return routeTree
  },
}
