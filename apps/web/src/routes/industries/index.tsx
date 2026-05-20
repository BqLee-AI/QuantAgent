import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

export const Route = createFileRoute('/industries/')({
  component: IndustriesPage,
})

function IndustriesPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Industries</p>
        <h1 className="page-title">Industries</h1>
        <p className="page-description">
          Industry package workspace for future domain modules, market coverage, and source binding context.
        </p>
      </section>

      <section className={styles.overviewGrid} aria-label="Industries overview">
        <PlaceholderPanel title="Packages" copy="Industry modules and domain boundaries will be summarized here." />
        <PlaceholderPanel title="Markets" copy="Market coverage and source binding context will be reviewed here." />
        <PlaceholderPanel title="Dependencies" copy="Future package readiness and dependency signals will appear here." />
      </section>
    </>
  )
}
