import { Button, Input } from '@heroui/react'
import { createFileRoute } from '@tanstack/react-router'
import { EventBadge, PageHero, SectionCard } from '@/shared/ui/theme-primitives'

export const Route = createFileRoute('/events/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('events:read')) throw redirect({ to: '/' })
  },
  component: EventsPage,
})

const EVENT_STREAM = [
  {
    impact: 'NVDA guidance revised by two supply-chain analysts within 14m.',
    latency: '42s ingest',
    source: 'Analyst pulse',
    tone: 'risk-increase',
    title: 'Semiconductor basket repricing risk',
  },
  {
    impact: 'USD liquidity signal widened to 3 sectors and 2 crypto pairs.',
    latency: '1m 12s ingest',
    source: 'Macro feed',
    tone: 'risk-reduce',
    title: 'Cross-asset funding stress eased',
  },
  {
    impact: 'A human approval is required before webhook-triggered execution resumes.',
    latency: '9m remaining',
    source: 'Approval bridge',
    tone: 'approval-expiring',
    title: 'Execution window waiting for HITL confirmation',
  },
] as const

function EventsPage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Events"
        title="视觉 token 已直接驱动事件视图的语义状态"
        description="事件页不再直接写 gray 或 blue。风险、缓释、审批倒计时都走 DESIGN token → CSS 变量 → Tailwind utility / HeroUI semantic 的单一路径。"
        actions={
          <>
            <Input
              aria-label="Search event stream"
              className="w-full sm:w-[320px]"
              placeholder="Search event stream"
              variant="secondary"
            />
            <Button variant="primary">Filter High Risk</Button>
          </>
        }
        stats={[
          { label: 'Active signals', value: '128' },
          { label: 'Escalations', tone: 'risk-increase', value: '07' },
          { label: 'Recovered paths', tone: 'risk-reduce', value: '19' },
        ]}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <SectionCard
          title="Event Inbox"
          description="EventBadge 的圆角、内边距与语义背景通过统一类名落地，AI 生成新事件行时只需组合这些语义 primitive。"
        >
          <div className="space-y-3">
            {EVENT_STREAM.map((event) => (
              <article key={event.title} className="qa-list-row">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-2">
                    <div className="qa-list-kicker">{event.source}</div>
                    <h2 className="text-title-sm font-semibold text-ink">{event.title}</h2>
                    <p className="text-body-md text-muted-strong">{event.impact}</p>
                  </div>
                  <div className="flex flex-col items-start gap-2 md:items-end">
                    <EventBadge tone={event.tone}>{event.latency}</EventBadge>
                    <span className="qa-inline-code text-number-sm text-muted">{event.source}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="Token Wiring"
          description="这三个语义是 issue #11 的关键验收路径。"
        >
          <div className="space-y-3 text-body-md">
            <div className="qa-token-row">
              <span className="font-semibold text-ink">risk-increase</span>
              <code className="qa-code">--qa-color-risk-increase → text-risk-increase → HeroUI danger</code>
            </div>
            <div className="qa-token-row">
              <span className="font-semibold text-ink">risk-reduce</span>
              <code className="qa-code">--qa-color-risk-reduce → text-risk-reduce → HeroUI success</code>
            </div>
            <div className="qa-token-row">
              <span className="font-semibold text-ink">approval-expiring</span>
              <code className="qa-code">--qa-color-approval-expiring → text-approval-expiring → HeroUI warning</code>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
