import { createFileRoute } from '@tanstack/react-router'
import { PageEmpty } from '../../app/components/PageEmpty'
import { PageLoading } from '../../app/components/PageLoading'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

type SettingsPreviewState = 'loading' | 'empty'

type SettingsSearch = {
  state?: SettingsPreviewState
}

export const Route = createFileRoute('/settings/')({
  validateSearch: (search): SettingsSearch => ({
    state: isSettingsPreviewState(search.state) ? search.state : undefined,
  }),
  component: SettingsPage,
})

function SettingsPage() {
  const { state } = Route.useSearch()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Settings</p>
        <h1 className="page-title">Settings</h1>
        <p className="page-description">
          Local authentication, notification channels, secret references, authorization policy, and realtime status.
        </p>
      </section>

      {state === 'loading' ? <PageLoading message="Loading settings workspace..." /> : null}

      {state === 'empty' ? (
        <PageEmpty
          title="No settings configured"
          description="The settings workspace has no access policies, notification channels, or secret references to show in this preview state."
          cta={
            <button className={styles.previewAction} type="button">
              Preview setup action
            </button>
          }
        />
      ) : null}

      {!state ? (
        <section className={styles.overviewGrid} aria-label="Settings overview">
          <PlaceholderPanel title="Access" copy="Session configuration and capability visibility." />
          <PlaceholderPanel title="Notifications" copy="Channel setup and delivery health for operator alerts." />
          <PlaceholderPanel title="Secrets" copy="Secret references and policy-controlled management entry points." />
        </section>
      ) : null}
    </>
  )
}

function isSettingsPreviewState(value: unknown): value is SettingsPreviewState {
  return value === 'loading' || value === 'empty'
}
