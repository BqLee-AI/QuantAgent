import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { useEffect, useState, type FormEvent } from 'react'

import { ApiError } from '../../shared/api'
import { useAuth } from '../../shared/auth'

type LoginSearch = {
  redirect?: string
}

export const Route = createFileRoute('/(public)/login')({
  validateSearch: (search): LoginSearch => ({
    redirect: typeof search.redirect === 'string' ? search.redirect : undefined,
  }),
  beforeLoad: ({ context, search }) => {
    if (context.auth?.status === 'authenticated') {
      throw redirect({ to: normalizeRedirect(search.redirect) })
    }
  },
  component: SignInPage,
})

function SignInPage() {
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
    <main className="grid min-h-screen place-items-center bg-canvas px-lg py-lg">
      <section
        className="grid w-full max-w-[420px] gap-lg rounded-lg border border-hairline bg-canvas px-xl py-xl shadow-elevated"
        aria-labelledby="signin-title"
      >
        <div className="grid gap-xs">
          <div className="flex items-center gap-sm text-title-sm font-bold text-ink">
            <span
              className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-body-sm font-bold text-on-primary"
              aria-hidden="true"
            >
              Q
            </span>
            <span>QuantAgent</span>
          </div>
          <h1 id="signin-title" className="m-0 text-title-lg font-bold text-ink">
            登录
          </h1>
          <p className="m-0 text-body-md text-muted">
            使用本地管理员密码进入运行控制台。
          </p>
        </div>

        <form className="grid gap-md" onSubmit={handleSubmit}>
          <label className="grid gap-xs">
            <span className="text-body-sm font-bold text-muted-strong">管理员密码</span>
            <input
              className="min-h-[42px] w-full rounded-lg border border-hairline-strong bg-canvas px-md text-body-md text-ink outline-2 outline-offset-1 outline-transparent transition-[border-color,outline-color] focus:border-primary focus:outline-[rgb(59_130_246_/_0.18)]"
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error ? (
            <p className="m-0 text-body-sm text-trading-down" role="alert">
              {error}
            </p>
          ) : null}

          <button
            className="min-h-[42px] rounded-lg border border-primary bg-primary text-body-md font-bold text-on-primary transition-colors hover:bg-primary-active disabled:cursor-not-allowed disabled:border-primary-disabled disabled:bg-primary-disabled"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? '登录中...' : '登录'}
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
    return error.status === 401 ? '密码不正确。' : error.msg
  }

  return '登录失败。'
}
