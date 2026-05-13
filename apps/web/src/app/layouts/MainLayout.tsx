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

function Sidebar() {
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <aside className="fixed left-0 top-0 z-30 flex h-screen w-[240px] flex-col border-r border-gray-200 bg-white">
      <div className="flex h-[56px] items-center gap-2.5 border-b border-gray-200 px-5">
        <span className="text-lg font-bold text-blue-500">◆</span>
        <span className="text-base font-bold text-gray-900">QuantAgent</span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-3">
        {NAV_ITEMS.map((item) => {
          const isActive = currentPath.startsWith(`/${item.to.slice(1)}`)
          return (
            <Link
              key={item.to}
              to={item.to}
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
  )
}

export function MainLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />
      <div className="pl-[240px]">
        <header className="sticky top-0 z-20 flex h-[56px] items-center border-b border-gray-200 bg-white px-6">
          <Breadcrumbs />
        </header>
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
