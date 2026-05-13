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

function Breadcrumbs() {
  const router = useRouterState()
  const matches = router.location.pathname.split('/').filter(Boolean)

  if (matches.length === 0) return null

  return (
    <nav className="flex items-center gap-1.5 text-sm text-gray-500">
      <Link to="/" className="hover:text-gray-900">
        Home
      </Link>
      {matches.map((segment, i) => (
        <span key={i} className="flex items-center gap-1.5">
          <span className="text-gray-300">/</span>
          <span
            className={cn(
              'capitalize',
              i === matches.length - 1 ? 'text-gray-900 font-medium' : 'hover:text-gray-900',
            )}
          >
            {segment}
          </span>
        </span>
      ))}
    </nav>
  )
}

function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'fixed left-0 top-0 z-50 flex h-screen w-[240px] flex-col border-r border-gray-200 bg-white transition-transform md:static md:z-30 md:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-[56px] items-center gap-2.5 border-b border-gray-200 px-5">
          <span className="text-lg font-bold text-blue-500">◆</span>
          <span className="text-base font-bold text-gray-900">QuantAgent</span>
          <button
            className="ml-auto text-gray-400 hover:text-gray-600 md:hidden"
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
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                )}
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </Link>
            )
          })}
        </nav>
      </aside>
    </>
  )
}

export function MainLayout() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 md:flex">
      <Sidebar open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-[56px] items-center border-b border-gray-200 bg-white px-4 md:px-6">
          <button
            className="mr-3 text-gray-600 hover:text-gray-900 md:hidden"
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
