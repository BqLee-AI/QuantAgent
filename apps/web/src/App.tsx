import { createRouter, RouterProvider } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'

const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

/** Application entry component — bootstraps TanStack Router with the generated route tree. */
export default function App() {
  return <RouterProvider router={router} />
}
