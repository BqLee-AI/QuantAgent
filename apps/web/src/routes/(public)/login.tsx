import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { useEffect, useState, type FormEvent } from 'react'

import { ApiError } from '../../shared/api'
import { useAuth } from '../../shared/auth'
import { useRuntimeConfig } from '../../shared/config'

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
  const runtimeConfig = useRuntimeConfig()
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
    <main className="grid min-h-screen place-items-center bg-[radial-gradient(circle_at_top_left,rgba(3,105,161,0.12),transparent_28%),linear-gradient(180deg,rgb(247,250,252),rgb(241,245,249))] px-lg py-lg">
      <section
        className="grid w-full max-w-[960px] gap-lg rounded-[28px] border border-hairline bg-canvas/95 p-lg shadow-elevated lg:grid-cols-[minmax(0,1.1fr)_420px] lg:p-xl"
        aria-labelledby="signin-title"
      >
        <div className="grid content-between gap-6 rounded-[24px] bg-[linear-gradient(135deg,rgba(2,132,199,0.08),rgba(14,165,233,0.03))] p-lg">
          <div className="grid gap-4">
            <div className="flex items-center gap-sm text-title-sm font-bold text-ink">
              <span
                className="grid h-9 w-9 place-items-center rounded-xl bg-primary text-body-sm font-bold text-on-primary"
                aria-hidden="true"
              >
                Q
              </span>
              <span>QuantAgent</span>
            </div>
            <div className="grid gap-2">
              <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(3,105,161)]">
                内部运行时管理台
              </p>
              <h1 id="signin-title" className="m-0 text-[30px] leading-[1.08] font-bold text-ink">
                事件驱动的量化分析与人工审批工作台
              </h1>
              <p className="m-0 max-w-[48ch] text-body-md text-muted">
                前端不直接放行高风险执行，所有高风险动作都需要经过审批链路和 Policy Gate。
              </p>
            </div>
          </div>

          <div className="grid gap-3">
            <div className="rounded-2xl border border-hairline bg-canvas p-4">
              <p className="m-0 text-[12px] font-bold text-muted-strong">当前环境</p>
              <p className="mt-1 mb-0 text-body-sm text-muted">模式：{runtimeConfig.mode}</p>
              <p className="m-0 text-body-sm text-muted">
                鉴权状态：{runtimeConfig.authEnabled ? '已开启' : '已关闭'}
              </p>
              <p className="m-0 text-body-sm text-muted">
                直入能力：{runtimeConfig.authEnabled ? '关闭' : '允许本地开发自动进入'}
              </p>
            </div>
            {!runtimeConfig.authEnabled ? (
              <div className="rounded-2xl border border-[rgb(14,165,233,0.16)] bg-[rgb(224,242,254)] p-4 text-body-sm text-[rgb(7,89,133)]">
                开发环境已关闭鉴权。若后端返回开发态会话，页面会自动进入 Dashboard；这里仍保留登录表单以便验证登录流。
              </div>
            ) : null}
          </div>
        </div>

        <div className="grid gap-lg rounded-[24px] border border-hairline bg-canvas px-xl py-xl">
          <div className="grid gap-xs">
            <h2 className="m-0 text-title-lg font-bold text-ink">登录</h2>
            <p className="m-0 text-body-md text-muted">
              登录成功后跳转到 Dashboard，再从 Dashboard 进入事件、审批或运行态。
            </p>
          </div>

          <form className="grid gap-md" onSubmit={handleSubmit}>
            <label className="grid gap-xs">
              <span className="text-body-sm font-bold text-muted-strong">用户名或邮箱</span>
              <input
                aria-label="用户名或邮箱"
                className="min-h-[42px] w-full rounded-lg border border-hairline-strong bg-canvas px-md text-body-md text-ink outline-2 outline-offset-1 outline-transparent transition-[border-color,outline-color] focus:border-primary focus:outline-[rgb(59_130_246_/_0.18)]"
                autoComplete="username"
                disabled
                name="username"
                placeholder="当前本地模式暂未接入用户名字段"
                type="text"
                value="local_admin"
              />
            </label>

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
        </div>
      </section>
    </main>
  )
}

function normalizeRedirect(value: string | undefined): string {
  if (!value || !value.startsWith('/') || value.startsWith('//') || value === '/login') {
    return '/'
  }

  return value
}

function toLoginMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.status === 401 ? '密码不正确。' : error.msg
  }

  return '登录失败。'
}
