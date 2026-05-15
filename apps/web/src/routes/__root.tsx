import { createRootRouteWithContext } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'

import { MainLayout } from '../app/layouts/MainLayout'
import type { RouterContext } from '../app/router'

export const Route = createRootRouteWithContext<RouterContext>()({
  beforeLoad: ({ context }) => {
    void context.capabilities
  },
  component: RootRoute,
})

function RootRoute() {
  return (
    <>
      <MainLayout />
      <TanStackRouterDevtools />
    </>
  )
}
