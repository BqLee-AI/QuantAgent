import { createFileRoute } from '@tanstack/react-router'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

export const Route = createFileRoute('/skills/')({
  component: SkillsPage,
})

function SkillsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Skills</p>
        <h1 className="page-title">Skills</h1>
        <p className="page-description">
          Skill registry workspace for future capability discovery, configuration review, and runtime readiness.
        </p>
      </section>

      <section className={styles.overviewGrid} aria-label="Skills overview">
        <PlaceholderPanel title="Catalog" copy="Registered skills and capability metadata will appear here." />
        <PlaceholderPanel title="Readiness" copy="Future checks for dependencies, permissions, and runtime availability." />
        <PlaceholderPanel title="Usage" copy="Operational visibility for skill adoption and execution patterns." />
      </section>
    </>
  )
}
