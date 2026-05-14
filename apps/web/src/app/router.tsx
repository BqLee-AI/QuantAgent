import { createRouter } from '@tanstack/react-router'

import { routeTree } from '../routeTree.gen'

export type RouterContext = {
  capabilities: Set<string>
}

export const router = createRouter({
  routeTree,
  context: {
    capabilities: new Set<string>(),
  },
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
