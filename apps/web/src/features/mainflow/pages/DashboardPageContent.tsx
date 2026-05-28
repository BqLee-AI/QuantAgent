import {
  Card,
  Chip,
} from '@heroui/react'

import {
  approvalsQueue,
  dashboardMetrics,
  featuredEvents,
  healthAlerts,
  walletMetrics,
} from '../mock-data'
import { ApprovalCard } from '../components/ApprovalCard'
import { EventCard } from '../components/EventCard'
import { HealthCard } from '../components/HealthCard'
import { LinkButton } from '../components/LinkButton'
import { WalletPnlChart } from '../components/WalletPnlChart'

export function DashboardPageContent() {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1.05fr)] xl:[grid-template-areas:'hero_wallet''metrics_wallet''feed_approvals''feed_health']">
      <Card
        className="border border-hairline bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.08),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.96))] xl:[grid-area:hero]"
      >
        <div className="grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end md:px-[18px]">
          <div className="grid gap-1.5">
            <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(5,150,105)]">
              Dashboard
            </p>
            <h1 className="m-0 text-[22px] leading-[1.05] font-bold text-ink sm:text-[24px] lg:text-[30px]">
              半导体新闻流
            </h1>
            <p className="m-0 text-body-sm text-muted">
              先看最有时效性的消息，再决定风险暴露和审批优先级。
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <LinkButton to="/events">事件中心</LinkButton>
            <LinkButton to="/approvals" variant="outline">审批队列</LinkButton>
            <LinkButton to="/runtime" variant="outline">运行态</LinkButton>
          </div>
        </div>
      </Card>

      <section
        aria-label="Dashboard 概览"
        className="grid gap-2.5 sm:grid-cols-2 xl:[grid-area:metrics] 2xl:grid-cols-4"
      >
        {dashboardMetrics.map((metric) => (
          <Card key={metric.label} className="border border-hairline bg-slate-50/80">
            <div className="grid gap-1 p-3">
              <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(5,150,105)]">
                {metric.label}
              </p>
              <p className="m-0 text-[22px] font-bold leading-[1.1] text-ink lg:text-[24px]">
                {metric.value}
              </p>
              <p className="m-0 text-[12px] text-muted">{metric.trend}</p>
            </div>
          </Card>
        ))}
      </section>

      <Card className="border border-hairline bg-white/90 xl:[grid-area:feed]">
        <div className="grid gap-3.5 p-3.5">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div className="grid gap-1">
              <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(5,150,105)]">
                重点快讯
              </p>
              <h2 className="m-0 text-title-md font-bold text-ink">
                今天最值得先看的三条
              </h2>
            </div>
            <LinkButton to="/events" variant="ghost">查看全部</LinkButton>
          </div>

          <div className="grid gap-2.5 lg:grid-cols-2">
            {featuredEvents.map((event, index) => (
              <div key={event.id} className={index === featuredEvents.length - 1 && featuredEvents.length % 2 === 1 ? 'lg:col-span-2' : ''}>
                <EventCard event={event} />
              </div>
            ))}
          </div>
        </div>
      </Card>

      <Card className="border border-hairline bg-white/95 xl:[grid-area:wallet]">
        <div className="grid gap-3 p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="grid gap-1">
              <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(5,150,105)]">
                钱包观察
              </p>
              <h2 className="m-0 text-title-sm font-bold text-ink">
                亏损与回撤
              </h2>
            </div>
            <Chip className="w-fit" variant="soft">钱包</Chip>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-3">
            {walletMetrics.map((metric) => (
              <Card key={metric.label} className="border border-black/5 bg-surface-soft">
                <div className="grid gap-1.5 p-3">
                  <p className="m-0 text-[12px] font-bold text-muted">{metric.label}</p>
                  <p className={`m-0 text-[20px] font-bold leading-[1.2] ${
                    metric.tone === 'negative'
                      ? 'text-trading-down'
                      : metric.tone === 'positive'
                        ? 'text-trading-up'
                        : 'text-ink'
                  }`}
                  >
                    {metric.value}
                  </p>
                  <p className="m-0 text-[12px] text-muted-strong">{metric.detail}</p>
                </div>
              </Card>
            ))}
          </div>

          <WalletPnlChart />
        </div>
      </Card>

      <Card className="border border-hairline bg-white/95 xl:[grid-area:approvals]">
        <div className="grid gap-2 p-3">
          <div className="grid gap-1">
            <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(5,150,105)]">
              审批压力
            </p>
            <h2 className="m-0 text-title-sm font-bold text-ink">
              待处理请求
            </h2>
          </div>

          <div className="grid gap-2">
            {approvalsQueue.map((approval) => (
              <ApprovalCard key={approval.id} approval={approval} />
            ))}
          </div>
        </div>
      </Card>

      <Card className="border border-hairline bg-white/95 xl:[grid-area:health]">
        <div className="grid gap-2 p-3">
          <div className="grid gap-1">
            <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(5,150,105)]">
              健康提醒
            </p>
            <h2 className="m-0 text-title-sm font-bold text-ink">
              关键异常
            </h2>
          </div>

          <div className="grid gap-2">
            {healthAlerts.map((alert) => (
              <HealthCard key={alert.id} alert={alert} />
            ))}
          </div>
        </div>
      </Card>
    </div>
  )
}
