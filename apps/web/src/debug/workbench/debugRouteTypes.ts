export type DebugPageState = 'overview' | 'loading' | 'empty' | 'empty-cta'
export type DebugRoutePreview = 'loading' | 'empty'

export type DebugPageRouteKey =
  | 'events'
  | 'runtime'
  | 'approvals'
  | 'plugins'
  | 'models'
  | 'settings'

export type DebugPageStatesSearch = {
  route?: DebugPageRouteKey
  state?: DebugPageState
}

export type DebugRoutePlaygroundSearch = {
  preview?: DebugRoutePreview
}

export type DebugPageRouteDefinition = {
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
