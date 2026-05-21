import { createFileRoute } from '@tanstack/react-router'
import { PageEmpty } from '../../app/components/PageEmpty'
import { PageLoading } from '../../app/components/PageLoading'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

type PluginsPreviewState = 'loading' | 'empty'

type PluginsSearch = {
  state?: PluginsPreviewState
}

export const Route = createFileRoute('/plugins/')({
  validateSearch: (search): PluginsSearch => ({
    state: isPluginsPreviewState(search.state) ? search.state : undefined,
  }),
  component: PluginsPage,
})

function PluginsPage() {
  const { state } = Route.useSearch()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Plugins</p>
        <h1 className="page-title">Plugin Management</h1>
        <p className="page-description">
          Plugin inventory for source, industry, strategy, notification, and executor integrations.
        </p>
      </section>

      {state === 'loading' ? <PageLoading message="Loading plugin inventory..." /> : null}

      {state === 'empty' ? (
        <PageEmpty
          title="No plugins available"
          description="The plugin workspace has no installed integrations or configuration records to show in this preview state."
          cta={
            <button className={styles.previewAction} type="button">
              Preview install flow
            </button>
          }
        />
      ) : null}

      {!state ? (
        <section className={styles.overviewGrid} aria-label="Plugins overview">
          <PlaceholderPanel title="Installed" copy="Registered plugins with type, version, and health status." />
          <PlaceholderPanel title="Configuration" copy="Schema-driven settings, secrets, validation, and audit trail." />
          <PlaceholderPanel title="Operations" copy="Enable, disable, reload, and inspect dependency failures." />
        </section>
      ) : null}
    </>
  )
}

function isPluginsPreviewState(value: unknown): value is PluginsPreviewState {
  return value === 'loading' || value === 'empty'
}
