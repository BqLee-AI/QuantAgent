import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/runtime/')({
  component: RuntimePage,
})

function RuntimePage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Runtime</p>
        <h1 className="page-title">Runtime Board</h1>
        <p className="page-description">
          Operational view for agent runs, tool invocations, scheduler activity, and runtime health signals.
        </p>
      </section>

      <section className="placeholder-grid" aria-label="Runtime overview">
        <PlaceholderPanel title="Agent Runs" copy="Recent runs, status transitions, and trace references." />
        <PlaceholderPanel title="Tool Calls" copy="Invocation status, retries, duration, and error summaries." />
        <PlaceholderPanel title="Scheduler" copy="Queued jobs, completed jobs, and runtime failures." />
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
