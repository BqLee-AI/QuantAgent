import { Link, Outlet, createRoute, useNavigate } from '@tanstack/react-router'
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
    label: 'Events',
    kicker: 'Event Inbox',
    title: 'Events',
    description:
      'Event intake and status review workspace for source events, analysis state, and related runtime traces.',
    loadingMessage: 'Loading event workspace...',
    emptyTitle: 'No events to review',
    emptyDescription: 'The event workspace has no source events ready for this preview state.',
    overview: [
      { title: 'Incoming', copy: 'Captured events waiting for routing and analysis.' },
      { title: 'In Progress', copy: 'Events currently connected to agent runs or plugin work.' },
      { title: 'Resolved', copy: 'Completed events with decisions, audit records, or approvals.' },
    ],
    ctaLabel: 'Preview action',
  },
  {
    key: 'runtime',
    label: 'Runtime',
    kicker: 'Runtime',
    title: 'Runtime Board',
    description:
      'Operational view for agent runs, tool invocations, scheduler activity, and runtime health signals.',
    loadingMessage: 'Loading runtime workspace...',
    emptyTitle: 'No runtime activity available',
    emptyDescription:
      'The runtime workspace has no agent runs, tool calls, or scheduler activity to show in this preview state.',
    overview: [
      { title: 'Agent Runs', copy: 'Recent runs, status transitions, and trace references.' },
      { title: 'Tool Calls', copy: 'Invocation status, retries, duration, and error summaries.' },
      { title: 'Scheduler', copy: 'Queued jobs, completed jobs, and runtime failures.' },
    ],
  },
  {
    key: 'approvals',
    label: 'Approvals',
    kicker: 'HITL',
    title: 'Approvals',
    description:
      'Human authorization queue for pending, expiring, handled, and automatically executed approval requests.',
    loadingMessage: 'Loading approvals workspace...',
    emptyTitle: 'No approvals to process',
    emptyDescription:
      'The approvals workspace has no pending, expiring, or handled requests to show in this preview state.',
    overview: [
      { title: 'Pending', copy: 'Requests waiting for approve, reject, reanalysis, or amend.' },
      { title: 'Expiring', copy: 'Short-window approvals that need attention before policy expiry.' },
      { title: 'Handled', copy: 'Approved, rejected, expired, or execute-then-notify decisions.' },
    ],
  },
  {
    key: 'plugins',
    label: 'Plugins',
    kicker: 'Plugins',
    title: 'Plugin Management',
    description:
      'Plugin inventory for source, industry, strategy, notification, and executor integrations.',
    loadingMessage: 'Loading plugin inventory...',
    emptyTitle: 'No plugins available',
    emptyDescription:
      'The plugin workspace has no installed integrations or configuration records to show in this preview state.',
    overview: [
      { title: 'Installed', copy: 'Registered plugins with type, version, and health status.' },
      { title: 'Configuration', copy: 'Schema-driven settings, secrets, validation, and audit trail.' },
      { title: 'Operations', copy: 'Enable, disable, reload, and inspect dependency failures.' },
    ],
    ctaLabel: 'Preview install flow',
  },
  {
    key: 'skills',
    label: 'Skills',
    kicker: 'Skills',
    title: 'Skills',
    description:
      'Skill registry workspace for future capability discovery, configuration review, and runtime readiness.',
    loadingMessage: 'Loading skill registry...',
    emptyTitle: 'No skills registered',
    emptyDescription:
      'The skills workspace has no capability entries or runtime readiness signals to show in this preview state.',
    overview: [
      { title: 'Catalog', copy: 'Registered skills and capability metadata will appear here.' },
      { title: 'Readiness', copy: 'Future checks for dependencies, permissions, and runtime availability.' },
      { title: 'Usage', copy: 'Operational visibility for skill adoption and execution patterns.' },
    ],
  },
  {
    key: 'tools',
    label: 'Tools',
    kicker: 'Tool Registry',
    title: 'Tools',
    description:
      'Tool registry workspace for future schema review, runtime availability, and integration boundaries.',
    loadingMessage: 'Loading tool registry...',
    emptyTitle: 'No tools available',
    emptyDescription:
      'The tools workspace has no registered schemas, availability signals, or ownership context to show in this preview state.',
    overview: [
      { title: 'Schemas', copy: 'Tool definitions, inputs, and outputs will be summarized here.' },
      { title: 'Availability', copy: 'Runtime health and compatibility signals will be reviewed here.' },
      { title: 'Sources', copy: 'Plugin and platform ownership context will be listed here.' },
    ],
  },
  {
    key: 'industries',
    label: 'Industries',
    kicker: 'Industries',
    title: 'Industries',
    description:
      'Industry package workspace for future domain modules, market coverage, and source binding context.',
    loadingMessage: 'Loading industry packages...',
    emptyTitle: 'No industry packages available',
    emptyDescription:
      'The industries workspace has no package coverage, market bindings, or dependency signals to show in this preview state.',
    overview: [
      { title: 'Packages', copy: 'Industry modules and domain boundaries will be summarized here.' },
      { title: 'Markets', copy: 'Market coverage and source binding context will be reviewed here.' },
      { title: 'Dependencies', copy: 'Future package readiness and dependency signals will appear here.' },
    ],
  },
  {
    key: 'settings',
    label: 'Settings',
    kicker: 'Settings',
    title: 'Settings',
    description:
      'Local authentication, notification channels, secret references, authorization policy, and realtime status.',
    loadingMessage: 'Loading settings workspace...',
    emptyTitle: 'No settings configured',
    emptyDescription:
      'The settings workspace has no access policies, notification channels, or secret references to show in this preview state.',
    overview: [
      { title: 'Access', copy: 'Session configuration and capability visibility.' },
      { title: 'Notifications', copy: 'Channel setup and delivery health for operator alerts.' },
      { title: 'Secrets', copy: 'Secret references and policy-controlled management entry points.' },
    ],
    ctaLabel: 'Preview setup action',
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
        <p className="page-kicker">Development Only</p>
        <h1 className="page-title">Debug Workbench</h1>
        <p className="page-description">
          Centralized development-only route workspace for page-state previews, runtime config inspection,
          fallback verification, and route-level experiments.
        </p>
      </section>

      <Outlet />
    </>
  )
}

function DebugWorkbenchIndexPage() {
  return (
    <>
      <section style={debugPanelGridStyle} aria-label="Debug route index">
        <PlaceholderPanel
          title="Page States"
          copy="Preview page-level loading, empty, and overview states without touching business-route query params."
        />
        <PlaceholderPanel
          title="Runtime Config"
          copy="Inspect the frontend-visible runtime config parse result without exposing hidden environment details."
        />
        <PlaceholderPanel
          title="Error Fallback"
          copy="Trigger the app-level error fallback with a controlled local failure path."
        />
        <PlaceholderPanel
          title="Route Playground"
          copy="Exercise route search params, unknown state handling, and local fallback behavior."
        />
      </section>

      <section style={actionRowStyle} aria-label="Debug route shortcuts">
        <Link to="/debug/page-states" style={primaryButtonStyle}>
          Open page states
        </Link>
        <Link to="/debug/runtime-config" style={secondaryButtonStyle}>
          Inspect runtime config
        </Link>
        <Link to="/debug/error-fallback" style={secondaryButtonStyle}>
          Trigger error fallback
        </Link>
        <Link to="/debug/route-playground" style={secondaryButtonStyle}>
          Open route playground
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
        <p className="page-kicker">Development Only</p>
        <h1 className="page-title">Page States</h1>
        <p className="page-description">
          Unified debug entry for page-level loading, empty, and overview previews. New page-state previews should
          land here instead of adding more business-route query params.
        </p>
      </section>

      <section style={actionRowStyle} aria-label="Page route selection">
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

      <section style={actionRowStyle} aria-label="Page state selection">
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
        <p className="page-kicker">Development Only</p>
        <h1 className="page-title">Runtime Config</h1>
        <p className="page-description">
          Frontend-visible runtime config parse result. This page only renders values already exposed to the web app.
        </p>
      </section>

      <section style={debugPanelGridStyle} aria-label="Runtime config snapshot">
        <PlaceholderPanel title="API Base URL" copy={runtimeConfig.apiBaseUrl || '(empty string)'} />
        <PlaceholderPanel title="WebSocket URL" copy={runtimeConfig.websocketUrl || '(empty string)'} />
        <PlaceholderPanel title="Mode" copy={runtimeConfig.mode} />
        <PlaceholderPanel title="Auth Enabled" copy={runtimeConfig.authEnabled ? 'true' : 'false'} />
      </section>
    </>
  )
}

function DebugErrorFallbackIndexPage() {
  const navigate = useNavigate()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Development Only</p>
        <h1 className="page-title">Error Fallback</h1>
        <p className="page-description">
          Trigger the app-level error boundary with a controlled local error path. No backend request is involved.
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
          Throw controlled render error
        </button>
      </section>

      <section style={{ marginTop: 'var(--qa-spacing-lg)' }}>
        <PlaceholderPanel
          title="Expected outcome"
          copy="The app should switch to the existing application error fallback, preserve safe error disclosure, and offer recovery actions."
        />
      </section>
    </>
  )
}

function DebugErrorFallbackThrowPage() {
  throw new Error('Debug fallback triggered from /debug/error-fallback.')
}

function DebugRoutePlaygroundPage({ preview }: { preview?: DebugRoutePreview }) {

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Development Only</p>
        <h1 className="page-title">Route Playground</h1>
        <p className="page-description">
          Verify search params, unknown state fallback, and route-level preview behavior without touching production routes.
        </p>
      </section>

      <section style={actionRowStyle}>
        <Link to="/debug/route-playground" style={!preview ? primaryButtonStyle : secondaryButtonStyle}>
          Default overview
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
          Add ignored param
        </Link>
      </section>

      {preview === 'loading' ? <PageLoading message="Loading route playground preview..." /> : null}

      {preview === 'empty' ? (
        <PageEmpty
          title="No route state selected"
          description="This empty preview confirms that the route playground can switch branches from local search params only."
        />
      ) : null}

      {!preview ? (
        <section style={debugPanelGridStyle} aria-label="Route playground overview">
          <PlaceholderPanel
            title="Search Param Branches"
            copy="Switch between controlled preview states and verify local fallback behavior."
          />
          <PlaceholderPanel
            title="Ignored Values"
            copy="Unexpected search params should be ignored instead of breaking the route."
          />
          <PlaceholderPanel
            title="Route Isolation"
            copy="Use this page to test route semantics without adding temporary behavior to formal business routes."
          />
        </section>
      ) : null}
    </>
  )
}

export const debugRouteApi: DebugRouteApi = {
  attachDebugRoutes: (routeTree) => {
    const existingChildren = Array.isArray(routeTree.children) ? routeTree.children : []

    if (existingChildren.some((child) => child.id === '/debug' || child.fullPath === '/debug')) {
      return routeTree
    }

    const debugRoute = createRoute({
      getParentRoute: () => routeTree,
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

    return routeTree.addChildren([...existingChildren, debugRouteTree])
  },
}
