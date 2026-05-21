import { createRootRouteWithContext, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'

import type { RouterContext } from '../app/router'

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootRoute,
})

function RootRoute() {
  return (
    <>
      <Outlet />
      {import.meta.env.DEV ? <TanStackRouterDevtools /> : null}
    </>
  )
}
