import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

export const Route = createFileRoute('/settings/')({
  component: SettingsPage,
})

function SettingsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Settings</p>
        <h1 className="page-title">Settings</h1>
        <p className="page-description">
          Local authentication, notification channels, secret references, authorization policy, and realtime status.
        </p>
      </section>

      <section className={styles.overviewGrid} aria-label="Settings overview">
        <PlaceholderPanel title="Access" copy="Session configuration and capability visibility." />
        <PlaceholderPanel title="Notifications" copy="Channel setup and delivery health for operator alerts." />
        <PlaceholderPanel title="Secrets" copy="Secret references and policy-controlled management entry points." />
      </section>
    </>
  )
}
