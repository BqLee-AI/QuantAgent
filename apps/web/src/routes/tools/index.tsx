import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

export const Route = createFileRoute('/tools/')({
  component: ToolsPage,
})

function ToolsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Tool Registry</p>
        <h1 className="page-title">Tools</h1>
        <p className="page-description">
          Tool registry workspace for future schema review, runtime availability, and integration boundaries.
        </p>
      </section>

      <section className={styles.overviewGrid} aria-label="Tools overview">
        <PlaceholderPanel title="Schemas" copy="Tool definitions, inputs, and outputs will be summarized here." />
        <PlaceholderPanel title="Availability" copy="Runtime health and compatibility signals will be reviewed here." />
        <PlaceholderPanel title="Sources" copy="Plugin and platform ownership context will be listed here." />
      </section>
    </>
  )
}
