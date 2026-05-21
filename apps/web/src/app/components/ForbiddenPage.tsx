import type { ReactNode } from 'react'

import type { ForbiddenDetails } from '../../shared/auth'

interface ForbiddenPageProps {
  details?: ForbiddenDetails | null
  onReturnToEntry?: () => void
}

const DEFAULT_MESSAGE = '当前账号没有执行该操作的权限。'

export function ForbiddenPage({
  details,
  onReturnToEntry,
}: ForbiddenPageProps): ReactNode {
  return (
    <section className="app-forbidden-screen">
      <section className="app-forbidden-card" aria-labelledby="app-forbidden-title">
        <p className="app-error-kicker">QuantAgent</p>
        <h1 id="app-forbidden-title" className="app-error-title">
          当前页面不可访问
        </h1>
        <p className="app-error-copy">
          你已经完成登录，但当前 capability 不允许进入这个工作区或执行该操作。
        </p>

        <div className="app-error-summary" role="status" aria-live="polite">
          <p className="app-error-summary-label">权限摘要</p>
          <p className="app-error-summary-value">{details?.message || DEFAULT_MESSAGE}</p>
        </div>

        {details?.requestId || details?.traceId ? (
          <dl className="app-error-meta">
            {details.requestId ? (
              <div className="app-error-meta-item">
                <dt className="app-error-meta-label">request_id</dt>
                <dd className="app-error-meta-value">{details.requestId}</dd>
              </div>
            ) : null}
            {details.traceId ? (
              <div className="app-error-meta-item">
                <dt className="app-error-meta-label">trace_id</dt>
                <dd className="app-error-meta-value">{details.traceId}</dd>
              </div>
            ) : null}
          </dl>
        ) : null}

        <div className="app-error-actions">
          <button
            type="button"
            className="app-error-button"
            onClick={() => {
              onReturnToEntry?.()
            }}
          >
            返回可访问入口
          </button>
        </div>
      </section>
    </section>
  )
}
