import { createRouter } from '@tanstack/react-router'

import { routeTree } from '../routeTree.gen'

export type RouterContext = {
  capabilities: Set<string>
}

export function createAppRouter() {
  return createRouter({
    routeTree,
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
