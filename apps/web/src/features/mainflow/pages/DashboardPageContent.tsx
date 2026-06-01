import { Card } from '@heroui/react'

import {
  dashboardMetrics,
  healthAlerts,
} from '../mock-data'
import { HealthCard } from '../components/HealthCard'
import { ApprovalScoreCard } from '@/features/event-scoring/components/ApprovalScoreCard'
import { DashboardEventSummaryCard } from '@/features/event-scoring/components/DashboardEventSummaryCard'
import {
  scoredApprovals,
  scoredEvents,
} from '@/features/event-scoring/mocks/event-scoring.mock'
import { selectDashboardHighlightedEvents } from '@/features/event-scoring/utils/event-scoring-selectors'
import { LinkButton } from '@/shared/ui'

export function DashboardPageContent() {
  const dashboardHighlightedEvents = selectDashboardHighlightedEvents(scoredEvents)
  const highlightedTitle = dashboardHighlightedEvents.length === 0
    ? '当前暂无符合条件的重点事件'
    : `今天最值得先看的 ${dashboardHighlightedEvents.length} 条`

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1.05fr)] xl:[grid-template-areas:'hero_side''metrics_side''events_approvals''events_health']">
      <Card className="border border-hairline bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.12),transparent_30%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.96))] xl:[grid-area:hero]">
        <div className="grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end md:px-[18px]">
          <div className="grid gap-1.5">
            <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(3,105,161)]">
              Dashboard
            </p>
            <h1 className="m-0 text-[24px] leading-[1.08] font-bold text-ink sm:text-[28px] lg:text-[32px]">
              今天先看什么
            </h1>
            <p className="m-0 max-w-[60ch] text-body-sm text-muted">
              首页只围绕重点事件、待处理审批和关键健康提醒组织，不替代事件中心、插件治理或运行排障页。
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <LinkButton to="/events">进入事件中心</LinkButton>
            <LinkButton to="/approvals" variant="outline">查看审批工作台</LinkButton>
            <LinkButton to="/runtime" variant="outline">查看运行态</LinkButton>
          </div>
        </div>
      </Card>

      <Card className="border border-hairline bg-white/95 xl:[grid-area:side]">
        <div className="grid gap-3 p-4">
          <div className="grid gap-1">
            <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(3,105,161)]">
              工作入口
            </p>
            <h2 className="m-0 text-title-sm font-bold text-ink">
              从首页继续进入主链路
            </h2>
          </div>
          <div className="grid gap-2">
            <LinkButton to="/events" className="justify-start" variant="outline">
              高价值事件中心
            </LinkButton>
            <LinkButton to="/approvals" className="justify-start" variant="outline">
              审批工作台
            </LinkButton>
            <LinkButton to="/runtime" className="justify-start" variant="outline">
              Runtime 排障页
            </LinkButton>
            <LinkButton to="/plugins" className="justify-start" variant="outline">
              Registry / Plugins
            </LinkButton>
            <LinkButton to="/models" className="justify-start" variant="outline">
              Model Providers / LLM Policies
            </LinkButton>
            <LinkButton to="/settings" className="justify-start" variant="outline">
              Settings
            </LinkButton>
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
              <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(3,105,161)]">
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

      <Card className="border border-hairline bg-white/90 xl:[grid-area:events]">
        <div className="grid gap-3.5 p-3.5">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div className="grid gap-1">
              <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(3,105,161)]">
                今日重点事件
              </p>
              <h2 className="m-0 text-title-md font-bold text-ink">
                {highlightedTitle}
              </h2>
            </div>
            <LinkButton to="/events" variant="ghost">查看全部事件</LinkButton>
          </div>

          {dashboardHighlightedEvents.length > 0 ? (
            <div className="grid gap-2.5 lg:grid-cols-2">
              {dashboardHighlightedEvents.map((event, index) => (
                <div key={event.id} className={index === dashboardHighlightedEvents.length - 1 && dashboardHighlightedEvents.length % 2 === 1 ? 'lg:col-span-2' : ''}>
                  <DashboardEventSummaryCard event={event} />
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-hairline-strong bg-surface p-4">
              <p className="m-0 text-body-sm text-muted">
                当前没有通过重点事件筛选的卡片，请前往事件中心查看完整列表。
              </p>
            </div>
          )}
        </div>
      </Card>

      <Card className="border border-hairline bg-white/95 xl:[grid-area:approvals]">
        <div className="grid gap-2 p-3">
          <div className="grid gap-1">
            <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(3,105,161)]">
              待处理审批
            </p>
            <h2 className="m-0 text-title-sm font-bold text-ink">
              只给摘要和入口，不在首页直接 approve / reject
            </h2>
          </div>

          <div className="grid gap-2">
            {scoredApprovals.map((approval) => (
              <ApprovalScoreCard key={approval.id} approval={approval} />
            ))}
          </div>
        </div>
      </Card>

      <Card className="border border-hairline bg-white/95 xl:[grid-area:health]">
        <div className="grid gap-2 p-3">
          <div className="grid gap-1">
            <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.04em] text-[rgb(3,105,161)]">
              关键健康提醒
            </p>
            <h2 className="m-0 text-title-sm font-bold text-ink">
              只展示影响判断质量的问题
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
