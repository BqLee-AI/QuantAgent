import { createFileRoute } from '@tanstack/react-router'
import { PageEmpty } from '../../app/components/PageEmpty'
import { PageLoading } from '../../app/components/PageLoading'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

type RuntimePreviewState = 'loading' | 'empty'

type RuntimeSearch = {
  state?: RuntimePreviewState
}

export const Route = createFileRoute('/runtime/')({
  validateSearch: (search): RuntimeSearch => ({
    state: isRuntimePreviewState(search.state) ? search.state : undefined,
  }),
  component: RuntimePage,
})

function RuntimePage() {
  const { state } = Route.useSearch()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Runtime</p>
        <h1 className="page-title">Runtime Board</h1>
        <p className="page-description">
          Operational view for agent runs, tool invocations, scheduler activity, and runtime health signals.
        </p>
      </section>

      {state === 'loading' ? <PageLoading message="Loading runtime workspace..." /> : null}

      {state === 'empty' ? (
        <PageEmpty
          title="No runtime activity available"
          description="The runtime workspace has no agent runs, tool calls, or scheduler activity to show in this preview state."
        />
      ) : null}

      {!state ? (
        <section className={styles.overviewGrid} aria-label="Runtime overview">
          <PlaceholderPanel title="Agent Runs" copy="Recent runs, status transitions, and trace references." />
          <PlaceholderPanel title="Tool Calls" copy="Invocation status, retries, duration, and error summaries." />
          <PlaceholderPanel title="Scheduler" copy="Queued jobs, completed jobs, and runtime failures." />
        </section>
      ) : null}
    </>
  )
}

function isRuntimePreviewState(value: unknown): value is RuntimePreviewState {
  return value === 'loading' || value === 'empty'
}
