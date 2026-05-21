import { createFileRoute } from '@tanstack/react-router'
import { PageEmpty } from '../../app/components/PageEmpty'
import { PageLoading } from '../../app/components/PageLoading'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

type ToolsPreviewState = 'loading' | 'empty'

type ToolsSearch = {
  state?: ToolsPreviewState
}

export const Route = createFileRoute('/tools/')({
  validateSearch: (search): ToolsSearch => ({
    state: isToolsPreviewState(search.state) ? search.state : undefined,
  }),
  component: ToolsPage,
})

function ToolsPage() {
  const { state } = Route.useSearch()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Tool Registry</p>
        <h1 className="page-title">Tools</h1>
        <p className="page-description">
          Tool registry workspace for future schema review, runtime availability, and integration boundaries.
        </p>
      </section>

      {state === 'loading' ? <PageLoading message="Loading tool registry..." /> : null}

      {state === 'empty' ? (
        <PageEmpty
          title="No tools available"
          description="The tools workspace has no registered schemas, availability signals, or ownership context to show in this preview state."
        />
      ) : null}

      {!state ? (
        <section className={styles.overviewGrid} aria-label="Tools overview">
          <PlaceholderPanel title="Schemas" copy="Tool definitions, inputs, and outputs will be summarized here." />
          <PlaceholderPanel title="Availability" copy="Runtime health and compatibility signals will be reviewed here." />
          <PlaceholderPanel title="Sources" copy="Plugin and platform ownership context will be listed here." />
        </section>
      ) : null}
    </>
  )
}

function isToolsPreviewState(value: unknown): value is ToolsPreviewState {
  return value === 'loading' || value === 'empty'
}
