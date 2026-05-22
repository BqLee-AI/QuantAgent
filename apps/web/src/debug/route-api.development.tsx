import { Link, Outlet, createRoute, useNavigate } from '@tanstack/react-router'
import type { AnyRoute } from '@tanstack/react-router'
import type { CSSProperties } from 'react'

import { PageEmpty } from '../app/components/PageEmpty'
import { PageLoading } from '../app/components/PageLoading'
import { PlaceholderPanel } from '../app/components/PlaceholderPanel'
import { loadRuntimeConfig } from '../shared/config'
import type { DebugRouteApi } from './route-api'

const debugPanelGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: '14px',
  marginTop: 'var(--qa-spacing-lg)',
}

const actionRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '12px',
  marginTop: 'var(--qa-spacing-lg)',
}

const secondaryButtonStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: '40px',
  padding: '0 16px',
  border: '1px solid var(--qa-color-border-strong)',
  borderRadius: 'var(--qa-radius-lg)',
  background: 'var(--qa-color-surface)',
  color: 'var(--qa-color-text-strong)',
  fontSize: '14px',
  fontWeight: 700,
  cursor: 'pointer',
}

const primaryButtonStyle: CSSProperties = {
  ...secondaryButtonStyle,
  border: '1px solid var(--qa-color-primary)',
  background: 'var(--qa-color-primary)',
  color: 'var(--qa-color-on-primary)',
}

type DebugPageState = 'overview' | 'loading' | 'empty' | 'empty-cta'
type DebugRoutePreview = 'loading' | 'empty'

type DebugPageRouteKey =
  | 'events'
  | 'runtime'
  | 'approvals'
  | 'plugins'
  | 'skills'
  | 'tools'
  | 'industries'
  | 'settings'

type DebugPageStatesSearch = {
  route?: DebugPageRouteKey
  state?: DebugPageState
}

type DebugRoutePlaygroundSearch = {
  preview?: DebugRoutePreview
}

type DebugPageRouteDefinition = {
  key: DebugPageRouteKey
  label: string
  kicker: string
  title: string
  description: string
  loadingMessage: string
  emptyTitle: string
  emptyDescription: string
  overview: Array<{ title: string; copy: string }>
  ctaLabel?: string
}

const debugPageStateOptions: DebugPageState[] = ['overview', 'loading', 'empty', 'empty-cta']

const debugPageRoutes: DebugPageRouteDefinition[] = [
  {
    key: 'events',
    label: '事件',
    kicker: '事件中心',
    title: '事件',
    description:
      '用于查看来源事件、分析状态和相关运行轨迹的事件接入与复核工作台。',
    loadingMessage: '正在加载事件工作台...',
    emptyTitle: '当前没有可处理事件',
    emptyDescription: '这个预览状态下还没有可供查看的来源事件。',
    overview: [
      { title: '待接入', copy: '已采集但尚未完成路由和分析的事件。' },
      { title: '处理中', copy: '已关联 Agent run、插件任务或人工处理流程的事件。' },
      { title: '已完成', copy: '已经形成决策、审计记录或审批结果的事件。' },
    ],
    ctaLabel: '预览操作',
  },
  {
    key: 'runtime',
    label: '运行时',
    kicker: '运行时',
    title: '运行时看板',
    description:
      '用于查看 Agent run、工具调用、调度器活动和运行时健康信号的运行看板。',
    loadingMessage: '正在加载运行时工作台...',
    emptyTitle: '当前没有运行时活动',
    emptyDescription:
      '这个预览状态下还没有 Agent run、工具调用或调度活动可供展示。',
    overview: [
      { title: 'Agent Runs', copy: '最近运行记录、状态流转和 trace 引用。' },
      { title: '工具调用', copy: '调用状态、重试情况、耗时和错误摘要。' },
      { title: '调度器', copy: '排队任务、已完成任务和运行失败情况。' },
    ],
  },
  {
    key: 'approvals',
    label: '审批',
    kicker: 'HITL',
    title: '审批',
    description:
      '用于处理待审批、即将过期、已处理和自动执行审批请求的人工授权队列。',
    loadingMessage: '正在加载审批工作台...',
    emptyTitle: '当前没有待处理审批',
    emptyDescription:
      '这个预览状态下还没有待处理、即将过期或已处理的审批请求可供展示。',
    overview: [
      { title: '待处理', copy: '等待批准、拒绝、重新分析或修订的请求。' },
      { title: '即将过期', copy: '需要在策略过期前尽快处理的短时效审批。' },
      { title: '已处理', copy: '已批准、已拒绝、已过期或执行后通知的决策记录。' },
    ],
  },
  {
    key: 'plugins',
    label: '插件',
    kicker: '插件',
    title: '插件管理',
    description:
      '用于查看来源、行业、策略、通知和执行器集成情况的插件清单。',
    loadingMessage: '正在加载插件清单...',
    emptyTitle: '当前没有可用插件',
    emptyDescription:
      '这个预览状态下还没有已安装集成或配置记录可供展示。',
    overview: [
      { title: '已安装', copy: '已注册插件的类型、版本和健康状态。' },
      { title: '配置', copy: '基于 schema 的设置、密钥引用、校验和审计轨迹。' },
      { title: '操作', copy: '启用、停用、重载以及依赖失败排查入口。' },
    ],
    ctaLabel: '预览安装流程',
  },
  {
    key: 'skills',
    label: '技能',
    kicker: '技能',
    title: '技能',
    description:
      '用于未来能力发现、配置检查和运行就绪性查看的技能注册工作台。',
    loadingMessage: '正在加载技能注册表...',
    emptyTitle: '当前没有已注册技能',
    emptyDescription:
      '这个预览状态下还没有能力条目或运行就绪信号可供展示。',
    overview: [
      { title: '目录', copy: '已注册技能和能力元数据会展示在这里。' },
      { title: '就绪性', copy: '后续会在这里检查依赖、权限和运行可用性。' },
      { title: '使用情况', copy: '用于查看技能采纳情况和执行模式的运行视角。' },
    ],
  },
  {
    key: 'tools',
    label: '工具',
    kicker: '工具注册表',
    title: '工具',
    description:
      '用于未来 schema 检查、运行可用性和集成边界核对的工具注册工作台。',
    loadingMessage: '正在加载工具注册表...',
    emptyTitle: '当前没有可用工具',
    emptyDescription:
      '这个预览状态下还没有已注册 schema、可用性信号或归属上下文可供展示。',
    overview: [
      { title: 'Schemas', copy: '工具定义、输入输出摘要会展示在这里。' },
      { title: '可用性', copy: '运行健康状态和兼容性信号会在这里查看。' },
      { title: '来源', copy: '插件和平台归属上下文会列在这里。' },
    ],
  },
  {
    key: 'industries',
    label: '行业包',
    kicker: '行业包',
    title: '行业包',
    description:
      '用于未来领域模块、市场覆盖和来源绑定上下文查看的行业包工作台。',
    loadingMessage: '正在加载行业包...',
    emptyTitle: '当前没有可用行业包',
    emptyDescription:
      '这个预览状态下还没有包覆盖范围、市场绑定或依赖信号可供展示。',
    overview: [
      { title: '包列表', copy: '行业模块和领域边界会汇总在这里。' },
      { title: '市场', copy: '市场覆盖和来源绑定上下文会在这里查看。' },
      { title: '依赖', copy: '后续的包就绪性和依赖信号会展示在这里。' },
    ],
  },
  {
    key: 'settings',
    label: '设置',
    kicker: '设置',
    title: '设置',
    description:
      '用于查看本地认证、通知渠道、密钥引用、授权策略和实时状态的设置工作台。',
    loadingMessage: '正在加载设置工作台...',
    emptyTitle: '当前没有已配置设置',
    emptyDescription:
      '这个预览状态下还没有访问策略、通知渠道或密钥引用可供展示。',
    overview: [
      { title: '访问', copy: '会话配置和能力可见性。' },
      { title: '通知', copy: '面向操作员提醒的渠道配置和投递健康状态。' },
      { title: '密钥', copy: '密钥引用和受策略控制的管理入口。' },
    ],
    ctaLabel: '预览设置操作',
  },
]

function isDebugPageRouteKey(value: unknown): value is DebugPageRouteKey {
  return debugPageRoutes.some((route) => route.key === value)
}

function isDebugPageState(value: unknown): value is DebugPageState {
  return debugPageStateOptions.includes(value as DebugPageState)
}

function isDebugRoutePreview(value: unknown): value is DebugRoutePreview {
  return value === 'loading' || value === 'empty'
}

function getDebugPageRoute(route: DebugPageRouteKey | undefined): DebugPageRouteDefinition {
  return debugPageRoutes.find((entry) => entry.key === route) ?? debugPageRoutes[0]
}

function DebugWorkbenchPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">仅开发环境</p>
        <h1 className="page-title">调试工作台</h1>
        <p className="page-description">
          用于集中承接页面状态预览、运行时配置检查、错误兜底验证和路由级实验的开发态工作台。
        </p>
      </section>

      <Outlet />
    </>
  )
}

function DebugWorkbenchIndexPage() {
  return (
    <>
      <section style={debugPanelGridStyle} aria-label="调试路由索引">
        <PlaceholderPanel
          title="页面状态"
          copy="在不修改业务路由 query 参数的前提下，预览页面级 loading、empty 和 overview 状态。"
        />
        <PlaceholderPanel
          title="运行时配置"
          copy="查看前端可见的运行时配置解析结果，不暴露隐藏环境细节。"
        />
        <PlaceholderPanel
          title="错误兜底"
          copy="通过受控的本地失败路径触发应用级错误兜底。"
        />
        <PlaceholderPanel
          title="路由实验场"
          copy="验证路由 search params、未知状态处理和本地 fallback 行为。"
        />
      </section>

      <section style={actionRowStyle} aria-label="调试路由快捷入口">
        <Link to="/debug/page-states" style={primaryButtonStyle}>
          打开页面状态
        </Link>
        <Link to="/debug/runtime-config" style={secondaryButtonStyle}>
          查看运行时配置
        </Link>
        <Link to="/debug/error-fallback" style={secondaryButtonStyle}>
          触发错误兜底
        </Link>
        <Link to="/debug/route-playground" style={secondaryButtonStyle}>
          打开路由实验场
        </Link>
      </section>
    </>
  )
}

function DebugPageStatesPage({
  route,
  state,
}: {
  route: DebugPageRouteKey
  state: DebugPageState
}) {
  const current = getDebugPageRoute(route)

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">仅开发环境</p>
        <h1 className="page-title">页面状态</h1>
        <p className="page-description">
          用于统一承接页面级 loading、empty 和 overview 预览。后续新增页面状态预览应优先放在这里，而不是继续叠加业务路由 query 参数。
        </p>
      </section>

      <section style={actionRowStyle} aria-label="页面路由选择">
        {debugPageRoutes.map((option) => (
          <Link
            key={option.key}
            to="/debug/page-states"
            search={{ route: option.key, state }}
            style={option.key === current.key ? primaryButtonStyle : secondaryButtonStyle}
          >
            {option.label}
          </Link>
        ))}
      </section>

      <section style={actionRowStyle} aria-label="页面状态选择">
        {debugPageStateOptions.map((option) => (
          <Link
            key={option}
            to="/debug/page-states"
            search={{ route: current.key, state: option }}
            style={option === state ? primaryButtonStyle : secondaryButtonStyle}
          >
            {option}
          </Link>
        ))}
      </section>

      <section style={{ marginTop: 'var(--qa-spacing-xl)' }}>
        <section className="page-header">
          <p className="page-kicker">{current.kicker}</p>
          <h2 className="page-title">{current.title}</h2>
          <p className="page-description">{current.description}</p>
        </section>

        {state === 'loading' ? <PageLoading message={current.loadingMessage} /> : null}

        {state === 'empty' ? (
          <PageEmpty title={current.emptyTitle} description={current.emptyDescription} />
        ) : null}

        {state === 'empty-cta' ? (
          <PageEmpty
            title={current.emptyTitle}
            description={current.emptyDescription}
            cta={
              current.ctaLabel ? (
                <button style={primaryButtonStyle} type="button">
                  {current.ctaLabel}
                </button>
              ) : undefined
            }
          />
        ) : null}

        {state === 'overview' ? (
          <section style={debugPanelGridStyle} aria-label={`${current.label} overview preview`}>
            {current.overview.map((panel) => (
              <PlaceholderPanel key={panel.title} title={panel.title} copy={panel.copy} />
            ))}
          </section>
        ) : null}
      </section>
    </>
  )
}

function DebugRuntimeConfigPage() {
  const runtimeConfig = loadRuntimeConfig()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">仅开发环境</p>
        <h1 className="page-title">运行时配置</h1>
        <p className="page-description">
          展示前端可见的运行时配置解析结果。本页只会渲染已经暴露给 Web 应用的值。
        </p>
      </section>

      <section style={debugPanelGridStyle} aria-label="运行时配置快照">
        <PlaceholderPanel title="API 基础地址" copy={runtimeConfig.apiBaseUrl || '（空字符串）'} />
        <PlaceholderPanel title="WebSocket 地址" copy={runtimeConfig.websocketUrl || '（空字符串）'} />
        <PlaceholderPanel title="运行模式" copy={runtimeConfig.mode} />
        <PlaceholderPanel title="是否开启认证" copy={runtimeConfig.authEnabled ? '是' : '否'} />
      </section>
    </>
  )
}

function DebugErrorFallbackIndexPage() {
  const navigate = useNavigate()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">仅开发环境</p>
        <h1 className="page-title">错误兜底</h1>
        <p className="page-description">
          通过受控的本地错误路径触发应用级错误边界，不依赖后端请求。
        </p>
      </section>

      <section style={actionRowStyle}>
        <button
          style={primaryButtonStyle}
          type="button"
          onClick={() => {
            void navigate({ to: '/debug/error-fallback/throw' })
          }}
        >
          触发受控渲染错误
        </button>
      </section>

      <section style={{ marginTop: 'var(--qa-spacing-lg)' }}>
        <PlaceholderPanel
          title="预期结果"
          copy="应用应切换到现有错误兜底页面，保持安全的错误展示方式，并提供恢复操作。"
        />
      </section>

      <Outlet />
    </>
  )
}

function DebugErrorFallbackThrowPage() {
  throw new Error('已从 /debug/error-fallback 触发调试错误兜底。')
}

function DebugRoutePlaygroundPage({ preview }: { preview?: DebugRoutePreview }) {

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">仅开发环境</p>
        <h1 className="page-title">路由实验场</h1>
        <p className="page-description">
          在不修改正式业务路由的前提下，验证 search params、未知状态 fallback 和路由级预览行为。
        </p>
      </section>

      <section style={actionRowStyle}>
        <Link to="/debug/route-playground" style={!preview ? primaryButtonStyle : secondaryButtonStyle}>
          默认概览
        </Link>
        <Link
          to="/debug/route-playground"
          search={{ preview: 'loading' }}
          style={preview === 'loading' ? primaryButtonStyle : secondaryButtonStyle}
        >
          preview=loading
        </Link>
        <Link
          to="/debug/route-playground"
          search={{ preview: 'empty' }}
          style={preview === 'empty' ? primaryButtonStyle : secondaryButtonStyle}
        >
          preview=empty
        </Link>
        <Link
          to="/debug/route-playground"
          search={{ preview: 'loading' as never, ignored: '1' as never }}
          style={secondaryButtonStyle}
        >
          添加忽略参数
        </Link>
      </section>

      {preview === 'loading' ? <PageLoading message="正在加载路由实验场预览..." /> : null}

      {preview === 'empty' ? (
        <PageEmpty
          title="当前没有选中路由状态"
          description="这个空态预览用于确认路由实验场只依赖本地 search params 就能切换分支。"
        />
      ) : null}

      {!preview ? (
        <section style={debugPanelGridStyle} aria-label="路由实验场概览">
          <PlaceholderPanel
            title="Search Param 分支"
            copy="在受控预览状态之间切换，并验证本地 fallback 行为。"
          />
          <PlaceholderPanel
            title="忽略值"
            copy="意外的 search params 应该被忽略，而不是破坏路由。"
          />
          <PlaceholderPanel
            title="路由隔离"
            copy="用这个页面验证路由语义，而不是把临时行为塞进正式业务路由。"
          />
        </section>
      ) : null}
    </>
  )
}

export const debugRouteApi: DebugRouteApi = {
  attachDebugRoutes: (routeTree) => {
    const rootChildren: AnyRoute[] = Array.isArray(routeTree.children) ? routeTree.children : []
    const workspaceRoute = rootChildren.find((child: AnyRoute) => child.id === '/_app/(workspace)')
    const workspaceChildren: AnyRoute[] = Array.isArray(workspaceRoute?.children)
      ? workspaceRoute.children
      : []

    if (
      workspaceChildren.some((child: AnyRoute) => child.id === '/debug' || child.fullPath === '/debug')
    ) {
      return routeTree
    }

    if (!workspaceRoute) {
      throw new Error('未找到 /_app/(workspace) layout route，无法挂载开发态 /debug 工作台。')
    }

    const debugRoute = createRoute({
      getParentRoute: () => workspaceRoute,
      path: '/debug',
      component: DebugWorkbenchPage,
    })

    const debugIndexRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: '/',
      component: DebugWorkbenchIndexPage,
    })

    const debugPageStatesRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'page-states',
      validateSearch: (search): DebugPageStatesSearch => ({
        route: isDebugPageRouteKey(search.route) ? search.route : 'events',
        state: isDebugPageState(search.state) ? search.state : 'overview',
      }),
      component: () => {
        const search = debugPageStatesRoute.useSearch()
        return <DebugPageStatesPage route={search.route ?? 'events'} state={search.state ?? 'overview'} />
      },
    })

    const debugRuntimeConfigRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'runtime-config',
      component: DebugRuntimeConfigPage,
    })

    const debugErrorFallbackRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'error-fallback',
      component: DebugErrorFallbackIndexPage,
    })

    const debugErrorFallbackThrowRoute = createRoute({
      getParentRoute: () => debugErrorFallbackRoute,
      path: 'throw',
      component: DebugErrorFallbackThrowPage,
    })

    const debugRoutePlaygroundRoute = createRoute({
      getParentRoute: () => debugRoute,
      path: 'route-playground',
      validateSearch: (search): DebugRoutePlaygroundSearch => ({
        preview: isDebugRoutePreview(search.preview) ? search.preview : undefined,
      }),
      component: () => {
        const search = debugRoutePlaygroundRoute.useSearch()
        return <DebugRoutePlaygroundPage preview={search.preview} />
      },
    })

    const debugErrorFallbackRouteTree = debugErrorFallbackRoute.addChildren([debugErrorFallbackThrowRoute])
    const debugRouteTree = debugRoute.addChildren([
      debugIndexRoute,
      debugPageStatesRoute,
      debugRuntimeConfigRoute,
      debugErrorFallbackRouteTree,
      debugRoutePlaygroundRoute,
    ])

    const workspaceRouteWithDebugChildren = workspaceRoute.addChildren([
      ...workspaceChildren,
      debugRouteTree,
    ])

    const nextRootChildren = rootChildren.map((child: AnyRoute) =>
      child.id === '/_app/(workspace)' ? workspaceRouteWithDebugChildren : child,
    )

    return routeTree.addChildren(nextRootChildren)
  },
}
