import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/events/')({
  component: EventsPage,
})

function EventsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Event Inbox</p>
        <h1 className="page-title">Events</h1>
        <p className="page-description">
          Event intake and status review workspace for source events, analysis state, and related runtime traces.
        </p>
      </section>

      <section className="placeholder-grid" aria-label="Events overview">
        <PlaceholderPanel title="Incoming" copy="Captured events waiting for routing and analysis." />
        <PlaceholderPanel title="In Progress" copy="Events currently connected to agent runs or plugin work." />
        <PlaceholderPanel title="Resolved" copy="Completed events with decisions, audit records, or approvals." />
      </section>
    </>
  )
}

function PlaceholderPanel({ title, copy }: { title: string; copy: string }) {
  return (
    <article className="placeholder-panel">
      <h2 className="placeholder-panel-title">{title}</h2>
      <p className="placeholder-panel-copy">{copy}</p>
    </article>
  )
}
