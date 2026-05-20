import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

export const Route = createFileRoute('/plugins/')({
  component: PluginsPage,
})

function PluginsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Plugins</p>
        <h1 className="page-title">Plugin Management</h1>
        <p className="page-description">
          Plugin inventory for source, industry, strategy, notification, and executor integrations.
        </p>
      </section>

      <section className={styles.overviewGrid} aria-label="Plugins overview">
        <PlaceholderPanel title="Installed" copy="Registered plugins with type, version, and health status." />
        <PlaceholderPanel title="Configuration" copy="Schema-driven settings, secrets, validation, and audit trail." />
        <PlaceholderPanel title="Operations" copy="Enable, disable, reload, and inspect dependency failures." />
      </section>
    </>
  )
}
