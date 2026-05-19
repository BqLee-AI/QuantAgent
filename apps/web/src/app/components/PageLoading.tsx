import styles from './PageLoading.module.css'

export function PageLoading({ message = 'Loading page state...' }: { message?: string }) {
  return (
    <section className={styles.state} role="status" aria-live="polite" aria-busy="true">
      <span className={styles.mark} aria-hidden="true" />
      <p className={styles.title}>{message}</p>
    </section>
  )
}
