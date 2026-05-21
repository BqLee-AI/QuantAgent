import { createFileRoute } from '@tanstack/react-router'
import { PageEmpty } from '../../app/components/PageEmpty'
import { PageLoading } from '../../app/components/PageLoading'
import { PlaceholderPanel } from '../../app/components/PlaceholderPanel'
import styles from './index.module.css'

type SkillsPreviewState = 'loading' | 'empty'

type SkillsSearch = {
  state?: SkillsPreviewState
}

export const Route = createFileRoute('/skills/')({
  validateSearch: (search): SkillsSearch => ({
    state: isSkillsPreviewState(search.state) ? search.state : undefined,
  }),
  component: SkillsPage,
})

function SkillsPage() {
  const { state } = Route.useSearch()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Skills</p>
        <h1 className="page-title">Skills</h1>
        <p className="page-description">
          Skill registry workspace for future capability discovery, configuration review, and runtime readiness.
        </p>
      </section>

      {state === 'loading' ? <PageLoading message="Loading skill registry..." /> : null}

      {state === 'empty' ? (
        <PageEmpty
          title="No skills registered"
          description="The skills workspace has no capability entries or runtime readiness signals to show in this preview state."
        />
      ) : null}

      {!state ? (
        <section className={styles.overviewGrid} aria-label="Skills overview">
          <PlaceholderPanel title="Catalog" copy="Registered skills and capability metadata will appear here." />
          <PlaceholderPanel
            title="Readiness"
            copy="Future checks for dependencies, permissions, and runtime availability."
          />
          <PlaceholderPanel title="Usage" copy="Operational visibility for skill adoption and execution patterns." />
        </section>
      ) : null}
    </>
  )
}

function isSkillsPreviewState(value: unknown): value is SkillsPreviewState {
  return value === 'loading' || value === 'empty'
}
