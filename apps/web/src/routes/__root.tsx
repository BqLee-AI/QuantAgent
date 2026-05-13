import { createRootRoute } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { MainLayout } from '@/app/layouts/MainLayout'

export const Route = createRootRoute({
  component: RootComponent,
  notFoundComponent: () => (
    <div className="qa-panel mx-auto flex max-w-xl flex-col items-center justify-center gap-2 px-6 py-20 text-center text-muted">
      <h2 className="text-title-lg font-semibold text-ink">404</h2>
      <p className="text-body-md">Page not found</p>
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
