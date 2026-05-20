import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

export const Route = createFileRoute('/approvals/')({
  component: ApprovalsPage,
})

function ApprovalsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">HITL</p>
        <h1 className="page-title">Approvals</h1>
        <p className="page-description">
          Human authorization queue for pending, expiring, handled, and automatically executed approval requests.
        </p>
      </section>

      <section className={styles.overviewGrid} aria-label="Approvals overview">
        <PlaceholderPanel title="Pending" copy="Requests waiting for approve, reject, reanalysis, or amend." />
        <PlaceholderPanel title="Expiring" copy="Short-window approvals that need attention before policy expiry." />
        <PlaceholderPanel title="Handled" copy="Approved, rejected, expired, or execute-then-notify decisions." />
      </section>
    </>
  )
}
