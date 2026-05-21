import { createFileRoute } from '@tanstack/react-router'
import { PageEmpty } from '../../app/components/PageEmpty'
import { PageLoading } from '../../app/components/PageLoading'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

type ApprovalsPreviewState = 'loading' | 'empty'

type ApprovalsSearch = {
  state?: ApprovalsPreviewState
}

export const Route = createFileRoute('/approvals/')({
  validateSearch: (search): ApprovalsSearch => ({
    state: isApprovalsPreviewState(search.state) ? search.state : undefined,
  }),
  component: ApprovalsPage,
})

function ApprovalsPage() {
  const { state } = Route.useSearch()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">HITL</p>
        <h1 className="page-title">Approvals</h1>
        <p className="page-description">
          Human authorization queue for pending, expiring, handled, and automatically executed approval requests.
        </p>
      </section>

      {state === 'loading' ? <PageLoading message="Loading approvals workspace..." /> : null}

      {state === 'empty' ? (
        <PageEmpty
          title="No approvals to process"
          description="The approvals workspace has no pending, expiring, or handled requests to show in this preview state."
        />
      ) : null}

      {!state ? (
        <section className={styles.overviewGrid} aria-label="Approvals overview">
          <PlaceholderPanel title="Pending" copy="Requests waiting for approve, reject, reanalysis, or amend." />
          <PlaceholderPanel title="Expiring" copy="Short-window approvals that need attention before policy expiry." />
          <PlaceholderPanel title="Handled" copy="Approved, rejected, expired, or execute-then-notify decisions." />
        </section>
      ) : null}
    </>
  )
}

function isApprovalsPreviewState(value: unknown): value is ApprovalsPreviewState {
  return value === 'loading' || value === 'empty'
}
