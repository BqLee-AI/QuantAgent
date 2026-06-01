import { Link, useRouterState } from '@tanstack/react-router'
import type { PropsWithChildren } from 'react'
import { listVisibleNavItems, useAuth } from '../../shared/auth'

const routeLabels = new Map<string, string>([
  ['agents', 'Agent Runs'],
  ['approvals', '审批'],
  ['audit', '审计时间线'],
  ['events', '事件'],
  ['models', '模型'],
  ['plugin-config-form', '插件配置表单'],
  ['plugins', '插件'],
  ['runtime', '运行态'],
  ['settings', '设置'],
  ['debug', '调试工作台'],
  ['page-states', '页面状态'],
  ['runtime-config', '运行时配置'],
  ['error-fallback', '错误兜底'],
  ['route-playground', '路由实验场'],
  ['tools', 'Tool Invocations'],
  ['approval-link', '一次性授权'],
  ['throw', '触发错误'],
])

export function MainLayout({ children }: PropsWithChildren) {
  const auth = useAuth()
  const pathname = useRouterState({ select: (state) => state.location.pathname })
  const breadcrumbs = getBreadcrumbs(pathname)
  const visibleNavItems = listVisibleNavItems(auth.capabilities)

  return (
    <div className="app-shell">
      <aside className="app-sidebar" aria-label="Primary navigation">
        <div className="app-brand">
          <span className="app-brand-mark">Q</span>
          <span>QuantAgent</span>
        </div>

        <nav className="app-nav">
          {visibleNavItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="app-nav-link"
              activeProps={{ className: 'app-nav-link app-nav-link-active' }}
              activeOptions={{ exact: item.to === '/' }}
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
                {index < breadcrumbs.length - 1 ? (
                  <Link to={breadcrumb.path} className="app-breadcrumb-link">
                    {breadcrumb.label}
                  </Link>
                ) : (
                  breadcrumb.label
                )}
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
  if (pathname === '/') {
    return [{ label: '仪表盘', path: '/' }]
  }

  if (pathname.startsWith('/approval-link/')) {
    return [
      { label: '一次性授权', path: '/approval-link' },
      { label: '授权详情', path: pathname },
    ]
  }

  if (pathname.startsWith('/events/')) {
    const segments = pathname.split('/').filter(Boolean)

    if (segments[2] === 'audit') {
      return [
        { label: '仪表盘', path: '/' },
        { label: '事件', path: '/events' },
        { label: '事件详情', path: `/events/${segments[1]}` },
        { label: '审计时间线', path: pathname },
      ]
    }

    return [
      { label: '仪表盘', path: '/' },
      { label: '事件', path: '/events' },
      { label: '事件详情', path: pathname },
    ]
  }

  if (pathname.startsWith('/approvals/')) {
    return [
      { label: '仪表盘', path: '/' },
      { label: '审批', path: '/approvals' },
      { label: '审批详情', path: pathname },
    ]
  }

  if (pathname.startsWith('/runtime/agents/')) {
    return [
      { label: '仪表盘', path: '/' },
      { label: '运行态', path: '/runtime' },
      { label: 'Agent Run 详情', path: pathname },
    ]
  }

  if (pathname.startsWith('/runtime/tools/')) {
    return [
      { label: '仪表盘', path: '/' },
      { label: '运行态', path: '/runtime' },
      { label: 'Tool Invocation 详情', path: pathname },
    ]
  }

  if (pathname.startsWith('/plugins/')) {
    return [
      { label: '仪表盘', path: '/' },
      { label: '插件', path: '/plugins' },
      { label: '插件详情', path: pathname },
    ]
  }

  const segments = pathname.split('/').filter(Boolean)

  return segments.map((segment, index) => {
    const path = `/${segments.slice(0, index + 1).join('/')}`

    return {
      label: index === 0 ? routeLabels.get(segment) ?? segment : segment,
      path,
    }
  })
}
