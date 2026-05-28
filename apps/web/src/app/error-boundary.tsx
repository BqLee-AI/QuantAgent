import { Component, type ErrorInfo, type ReactNode } from 'react'

export interface AppErrorDetails {
  summary: string
  requestId?: string
  traceId?: string
}

export interface AppErrorBoundaryProps {
  children: ReactNode
  fallback?: (error: AppErrorDetails) => ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface AppErrorBoundaryState {
  error: AppErrorDetails | null
}

const DEFAULT_ERROR_SUMMARY = '应用遇到错误。'
const DEFAULT_RUNTIME_TITLE = 'QuantAgent 遇到错误'
const DEFAULT_STARTUP_TITLE = 'QuantAgent 启动失败'
const DEFAULT_ENTRY_PATH = '/'

function normalizeSummary(value: string | undefined): string {
  const summary = value?.split(/\r?\n/, 1)[0]?.trim() ?? ''

  if (!summary) {
    return DEFAULT_ERROR_SUMMARY
  }

  return summary.length > 160 ? `${summary.slice(0, 157)}...` : summary
}

export function createAppErrorDetails(
  error: Error,
  context: Pick<AppErrorDetails, 'requestId' | 'traceId'> = {},
): AppErrorDetails {
  return {
    summary: normalizeSummary(error.message),
    requestId: context.requestId,
    traceId: context.traceId,
  }
}

export class AppErrorBoundary extends Component<
  AppErrorBoundaryProps,
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = {
    error: null,
  }

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error: createAppErrorDetails(error) }
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.props.onError?.(error, errorInfo)
  }

  override render(): ReactNode {
    if (this.state.error) {
      return this.props.fallback?.(this.state.error) ?? (
        <AppErrorScreen
          title={DEFAULT_RUNTIME_TITLE}
          description="应用在渲染时发生异常。"
          error={this.state.error}
        />
      )
    }

    return this.props.children
  }
}

export function StartupErrorFallback({ error }: { error?: Error }): ReactNode {
  return (
    <AppErrorScreen
      title={DEFAULT_STARTUP_TITLE}
      description="应用在启动或初始化阶段遇到错误。"
      error={error ? createAppErrorDetails(error) : { summary: DEFAULT_ERROR_SUMMARY }}
    />
  )
}

interface AppErrorScreenProps {
  title: string
  description: string
  error: AppErrorDetails
}

export function AppErrorScreen({
  title,
  description,
  error,
}: AppErrorScreenProps): ReactNode {
  return (
    <main className="app-error-screen">
      <section className="app-error-card" aria-labelledby="app-error-title">
        <p className="app-error-kicker">QuantAgent</p>
        <h1 id="app-error-title" className="app-error-title">
          {title}
        </h1>
        <p className="app-error-copy">{description}</p>

        <div className="app-error-summary" role="status" aria-live="polite">
          <p className="app-error-summary-label">错误摘要</p>
          <p className="app-error-summary-value">{error.summary}</p>
        </div>

        {error.requestId || error.traceId ? (
          <dl className="app-error-meta">
            {error.requestId ? (
              <div className="app-error-meta-item">
                <dt className="app-error-meta-label">request_id</dt>
                <dd className="app-error-meta-value">{error.requestId}</dd>
              </div>
            ) : null}
            {error.traceId ? (
              <div className="app-error-meta-item">
                <dt className="app-error-meta-label">trace_id</dt>
                <dd className="app-error-meta-value">{error.traceId}</dd>
              </div>
            ) : null}
          </dl>
        ) : null}

        <div className="app-error-actions">
          <button
            type="button"
            className="app-error-button"
            onClick={() => window.location.reload()}
          >
            重新加载
          </button>
          <a
            className="app-error-link"
            href={DEFAULT_ENTRY_PATH}
            onClick={(event) => {
              event.preventDefault()
              window.location.assign(DEFAULT_ENTRY_PATH)
            }}
          >
            返回默认入口
          </a>
        </div>
      </section>
    </main>
  )
}
