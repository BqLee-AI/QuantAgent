import styles from './PlaceholderPanel.module.css'

export function PlaceholderPanel({ title, copy }: { title: string; copy: string }) {
  return (
    <article className={styles.panel}>
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.copy}>{copy}</p>
    </article>
  )
}
