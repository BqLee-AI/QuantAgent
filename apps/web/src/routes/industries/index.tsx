import { createFileRoute } from '@tanstack/react-router'
import { PageEmpty } from '../../app/components/PageEmpty'
import { PageLoading } from '../../app/components/PageLoading'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

type IndustriesPreviewState = 'loading' | 'empty'

type IndustriesSearch = {
  state?: IndustriesPreviewState
}

export const Route = createFileRoute('/industries/')({
  validateSearch: (search): IndustriesSearch => ({
    state: isIndustriesPreviewState(search.state) ? search.state : undefined,
  }),
  component: IndustriesPage,
})

function IndustriesPage() {
  const { state } = Route.useSearch()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Industries</p>
        <h1 className="page-title">Industries</h1>
        <p className="page-description">
          Industry package workspace for future domain modules, market coverage, and source binding context.
        </p>
      </section>

      {state === 'loading' ? <PageLoading message="Loading industry packages..." /> : null}

      {state === 'empty' ? (
        <PageEmpty
          title="No industry packages available"
          description="The industries workspace has no package coverage, market bindings, or dependency signals to show in this preview state."
        />
      ) : null}

      {!state ? (
        <section className={styles.overviewGrid} aria-label="Industries overview">
          <PlaceholderPanel title="Packages" copy="Industry modules and domain boundaries will be summarized here." />
          <PlaceholderPanel title="Markets" copy="Market coverage and source binding context will be reviewed here." />
          <PlaceholderPanel
            title="Dependencies"
            copy="Future package readiness and dependency signals will appear here."
          />
        </section>
      ) : null}
    </>
  )
}

function isIndustriesPreviewState(value: unknown): value is IndustriesPreviewState {
  return value === 'loading' || value === 'empty'
}
