import { useState } from 'react'
import { Link, Outlet, useRouterState } from '@tanstack/react-router'
import { cn } from '@/shared/ui/cn'

const NAV_ITEMS = [
  { to: '/events' as const, label: 'Events', icon: '◉' },
  { to: '/runtime' as const, label: 'Runtime', icon: '▶' },
  { to: '/approvals' as const, label: 'Approvals', icon: '✓' },
  { to: '/plugins' as const, label: 'Plugins', icon: '⊞' },
  { to: '/settings' as const, label: 'Settings', icon: '⚙' },
] as const

/** Renders breadcrumb navigation derived from the current URL pathname. */
function Breadcrumbs() {
  const router = useRouterState()
  const matches = router.location.pathname.split('/').filter(Boolean)

  if (matches.length === 0) return null

  return (
    <nav className="flex items-center gap-1.5 text-body-sm text-muted">
      <Link to="/" className="transition-colors hover:text-ink">
        Home
      </Link>
      {matches.map((segment, i) => (
        <span key={i} className="flex items-center gap-1.5">
          <span className="text-hairline-dark">/</span>
          <span
            className={cn(
              'capitalize',
              i === matches.length - 1 ? 'font-medium text-ink' : 'transition-colors hover:text-ink',
            )}
          >
            {segment}
          </span>
        </span>
      ))}
    </nav>
  )
}

/** Responsive sidebar: always visible on desktop, drawer on mobile. */
function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-ink/20 backdrop-blur-[2px] md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'fixed left-0 top-0 z-50 flex h-screen w-[248px] flex-col border-r border-hairline-light bg-canvas-light transition-transform md:static md:z-30 md:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 items-center gap-2.5 border-b border-hairline-light px-5">
          <span className="text-lg font-bold text-primary">◆</span>
          <span className="text-base font-semibold text-ink">QuantAgent</span>
          <button
            className="ml-auto text-muted transition-colors hover:text-ink md:hidden"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-3">
          {NAV_ITEMS.map((item) => {
            const isActive =
              currentPath === item.to || currentPath.startsWith(`${item.to}/`)
            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={cn(
                  'flex items-center gap-2.5 rounded-lg border border-transparent px-3 py-2.5 text-body-md font-medium transition-colors',
                  isActive
                    ? 'border-hairline-light bg-surface-card text-ink'
                    : 'text-muted-strong hover:bg-surface-soft hover:text-ink',
                )}
              >
                <span className={cn('text-base', isActive ? 'text-primary' : 'text-muted')}>{item.icon}</span>
                {item.label}
              </Link>
            )
          })}
        </nav>
      </aside>
    </>
  )
}

/** Application shell with sidebar navigation, breadcrumb header, and scrollable content area. */
export function MainLayout() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <div className="min-h-screen bg-surface-soft md:flex">
      <Sidebar open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center border-b border-hairline-light bg-canvas-light/95 px-4 backdrop-blur md:px-6">
          <button
            className="mr-3 text-muted-strong transition-colors hover:text-ink md:hidden"
            onClick={() => setDrawerOpen(true)}
          >
            ☰
          </button>
          <Breadcrumbs />
        </header>
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
