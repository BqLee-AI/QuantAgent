import { useId, type ReactNode } from 'react'

import styles from './PageEmpty.module.css'

export function PageEmpty({
  title,
  description,
  cta,
}: {
  title: string
  description: string
  cta?: ReactNode
}) {
  const titleId = useId()

  return (
    <section className={`${styles.state} ${styles.stateEmpty}`} aria-labelledby={titleId}>
      <span className={styles.mark} aria-hidden="true">
        <span className={styles.markLine} />
        <span className={styles.markLine} />
      </span>
      <div className={styles.copy}>
        <p className={styles.eyebrow}>No content</p>
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        <p className={styles.description}>{description}</p>
      </div>
      {cta ? <div className={styles.actions}>{cta}</div> : null}
    </section>
  )
}
