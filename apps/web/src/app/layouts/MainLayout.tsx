import { Link, Outlet, useRouterState } from '@tanstack/react-router'

type NavItem = {
  label: string
  to: string
}

const navItems: NavItem[] = [
  { label: 'Events', to: '/events' },
  { label: 'Runtime', to: '/runtime' },
  { label: 'Approvals', to: '/approvals' },
  { label: 'Plugins', to: '/plugins' },
  { label: 'Settings', to: '/settings' },
]

const routeLabels = new Map<string, string>([
  ['events', 'Events'],
  ['runtime', 'Runtime'],
  ['approvals', 'Approvals'],
  ['plugins', 'Plugins'],
  ['settings', 'Settings'],
])

export function MainLayout() {
  const pathname = useRouterState({ select: (state) => state.location.pathname })
  const breadcrumbs = getBreadcrumbs(pathname)

  return (
    <div className="app-shell">
      <aside className="app-sidebar" aria-label="Primary navigation">
        <div className="app-brand">
          <span className="app-brand-mark">Q</span>
          <span>QuantAgent</span>
        </div>

        <nav className="app-nav">
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="app-nav-link"
              activeProps={{ className: 'app-nav-link app-nav-link-active' }}
              activeOptions={{ exact: false }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <nav className="app-breadcrumbs" aria-label="Breadcrumb">
            {breadcrumbs.map((breadcrumb, index) => (
              <span key={breadcrumb.path} className="app-breadcrumb-item">
                {index > 0 ? <span className="app-breadcrumb-separator">/</span> : null}
                {breadcrumb.label}
              </span>
            ))}
          </nav>
        </header>

        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function getBreadcrumbs(pathname: string) {
  const segments = pathname.split('/').filter(Boolean)

  if (segments.length === 0) {
    return [{ label: 'Events', path: '/events' }]
  }

  return segments.map((segment, index) => {
    const path = `/${segments.slice(0, index + 1).join('/')}`

    return {
      label: routeLabels.get(segment) ?? segment,
      path,
    }
  })
}
