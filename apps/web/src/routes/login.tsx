import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { useEffect, useState, type FormEvent } from 'react'

import { ApiError } from '../shared/api'
import { useAuth } from '../shared/auth'
import styles from './login.module.css'

type LoginSearch = {
  redirect?: string
}

export const Route = createFileRoute('/login')({
  validateSearch: (search): LoginSearch => ({
    redirect: typeof search.redirect === 'string' ? search.redirect : undefined,
  }),
  beforeLoad: ({ context, search }) => {
    if (context.auth?.status === 'authenticated') {
      throw redirect({ to: normalizeRedirect(search.redirect) })
    }
  },
  component: LoginPage,
})

function LoginPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const { redirect: redirectTo } = Route.useSearch()
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (auth.status === 'authenticated') {
      void navigate({ to: normalizeRedirect(redirectTo) })
    }
  }, [auth.status, navigate, redirectTo])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await auth.login(password)
      setPassword('')
      await navigate({ to: normalizeRedirect(redirectTo) })
    } catch (loginError) {
      setError(toLoginMessage(loginError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className={styles.shell}>
      <section className={styles.panel} aria-labelledby="login-title">
        <div className={styles.header}>
          <div className={styles.brand}>
            <span className={styles.mark} aria-hidden="true">Q</span>
            <span>QuantAgent</span>
          </div>
          <h1 id="login-title" className={styles.title}>Sign in</h1>
          <p className={styles.copy}>Use the local administrator password to open the runtime console.</p>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field}>
            <span className={styles.label}>Administrator password</span>
            <input
              className={styles.input}
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error ? <p className={styles.error} role="alert">{error}</p> : null}

          <button className={styles.button} disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}

function normalizeRedirect(value: string | undefined): string {
  if (!value || !value.startsWith('/') || value.startsWith('//') || value === '/login') {
    return '/events'
  }

  return value
}

function toLoginMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.status === 401 ? 'Password is invalid.' : error.msg
  }

  return 'Sign in failed.'
}
