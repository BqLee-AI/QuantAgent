import { createRootRoute } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { MainLayout } from '@/app/layouts/MainLayout'

export const Route = createRootRoute({
  component: RootComponent,
  notFoundComponent: () => (
    <div className="flex flex-col items-center justify-center py-20 text-gray-500">
      <h2 className="text-2xl font-bold text-gray-900">404</h2>
      <p className="mt-2">Page not found</p>
    </div>
  ),
})

/** Root route component — renders the shared layout and dev-only tools. */
function RootComponent() {
  return (
    <>
      <MainLayout />
      {import.meta.env.DEV && <TanStackRouterDevtools position="bottom-right" />}
    </>
  )
}
