import { Button } from '@heroui/react'
import { createFileRoute } from '@tanstack/react-router'
import { EventBadge, PageHero, SectionCard } from '@/shared/ui/theme-primitives'

export const Route = createFileRoute('/approvals/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('approvals:read')) throw redirect({ to: '/' })
  },
  component: ApprovalsPage,
})

const APPROVALS = [
  {
    eta: '12m left',
    owner: 'US macro strategy',
    tone: 'approval-expiring',
    title: 'Release broker adapter for CPI event playbook',
  },
  {
    eta: '2 reviewers',
    owner: 'Crypto execution',
    tone: 'risk-increase',
    title: 'Increase BTC perpetual notional cap during high-volatility window',
  },
] as const

function ApprovalsPage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Approvals"
        title="审批页使用 warning / danger 语义，而不是散落的局部色值"
        description="HeroUI danger 与 warning 已被桥接到设计 token。后续审批组件只要使用对应 variant，就会跟随 DESIGN 变量联动。"
        actions={
          <>
            <Button variant="secondary">Open Audit Log</Button>
            <Button variant="primary">Review Queue</Button>
          </>
        }
        stats={[
          { label: 'Pending approvals', value: '14' },
          { label: 'Expiring windows', tone: 'approval-expiring', value: '03' },
          { label: 'Manual blocks', tone: 'risk-increase', value: '02' },
        ]}
      />

      <SectionCard
        title="Approval Queue"
        description="审批倒计时和高风险动作分别映射到 warning 与 danger 语义。"
      >
        <div className="space-y-3">
          {APPROVALS.map((item) => (
            <article key={item.title} className="qa-list-row">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="space-y-2">
                  <div className="qa-list-kicker">{item.owner}</div>
                  <h2 className="text-title-sm font-semibold text-ink">{item.title}</h2>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <EventBadge tone={item.tone}>{item.eta}</EventBadge>
                  <Button variant="primary">Approve</Button>
                  <Button variant="danger">Reject</Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
