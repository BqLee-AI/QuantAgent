import { Link, useRouterState } from '@tanstack/react-router'
import type { PropsWithChildren } from 'react'
import { useAuth } from '../../shared/auth'

type NavItem = {
  label: string
  to: string
}

const navItems: NavItem[] = [
  { label: '事件', to: '/events' },
  { label: '运行态', to: '/runtime' },
  { label: '审批', to: '/approvals' },
  { label: '插件', to: '/plugins' },
  { label: '技能', to: '/skills' },
  { label: '工具', to: '/tools' },
  { label: '行业包', to: '/industries' },
  { label: '设置', to: '/settings' },
]

const routeLabels = new Map<string, string>([
  ['events', '事件'],
  ['runtime', '运行态'],
  ['approvals', '审批'],
  ['plugins', '插件'],
  ['skills', '技能'],
  ['tools', '工具'],
  ['industries', '行业包'],
  ['settings', '设置'],
])

export function MainLayout({ children }: PropsWithChildren) {
  const auth = useAuth()
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
          <div className="app-session" aria-label="Session status">
            {auth.isAuthDisabled ? (
              <span className="app-session-badge">开发环境已关闭鉴权</span>
            ) : null}
            {auth.actor ? (
              <span className="app-session-actor">{auth.actor.actor_id}</span>
            ) : null}
            <button className="app-session-logout" type="button" onClick={() => void auth.logout()}>
              退出登录
            </button>
          </div>
        </header>

        <main className="app-content">
          {children}
        </main>
      </div>
    </div>
  )
}

function getBreadcrumbs(pathname: string) {
  const segments = pathname.split('/').filter(Boolean)

  if (segments.length === 0) {
    return [{ label: '事件', path: '/events' }]
  }

  return segments.map((segment, index) => {
    const path = `/${segments.slice(0, index + 1).join('/')}`

    return {
      label: routeLabels.get(segment) ?? segment,
      path,
    }
  })
}
