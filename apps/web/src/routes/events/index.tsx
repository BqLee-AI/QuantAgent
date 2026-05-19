import { createFileRoute } from '@tanstack/react-router'
import { PageEmpty } from '../../app/components/PageEmpty'
import { PageLoading } from '../../app/components/PageLoading'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

type EventsPreviewState = 'loading' | 'empty'

type EventsSearch = {
  state?: EventsPreviewState
}

export const Route = createFileRoute('/events/')({
  validateSearch: (search): EventsSearch => ({
    state: isEventsPreviewState(search.state) ? search.state : undefined,
  }),
  component: EventsPage,
})

function EventsPage() {
  const { state } = Route.useSearch()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Event Inbox</p>
        <h1 className="page-title">Events</h1>
        <p className="page-description">
          Event intake and status review workspace for source events, analysis state, and related runtime traces.
        </p>
      </section>

      {state === 'loading' ? <PageLoading message="Loading event workspace..." /> : null}

      {state === 'empty' ? (
        <PageEmpty
          title="No events to review"
          description="The event workspace has no source events ready for this preview state."
          cta={
            <button className={styles.previewAction} type="button">
              Preview action
            </button>
          }
        />
      ) : null}

      {!state ? (
        <section className="placeholder-grid" aria-label="Events overview">
          <PlaceholderPanel title="Incoming" copy="Captured events waiting for routing and analysis." />
          <PlaceholderPanel title="In Progress" copy="Events currently connected to agent runs or plugin work." />
          <PlaceholderPanel title="Resolved" copy="Completed events with decisions, audit records, or approvals." />
        </section>
      ) : null}
    </>
  )
}

function isEventsPreviewState(value: unknown): value is EventsPreviewState {
  return value === 'loading' || value === 'empty'
}
