import { Button } from '@heroui/react'
import { createFileRoute } from '@tanstack/react-router'
import { EventBadge, PageHero, SectionCard } from '@/shared/ui/theme-primitives'

export const Route = createFileRoute('/plugins/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('plugins:read')) throw redirect({ to: '/' })
  },
  component: PluginsPage,
})

function PluginsPage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Plugins"
        title="AI 可直接复用语义 class 与 HeroUI variant 生成新插件卡片"
        description="这里刻意把 DESIGN 里的组件语言落成了可预测的 class 名和变体名，减少 AI 在新页面里猜测样式的空间。"
        actions={
          <>
            <Button variant="secondary">View Registry</Button>
            <Button variant="primary">Install Plugin</Button>
          </>
        }
        stats={[
          { label: 'Installed plugins', value: '09' },
          { label: 'Runtime safe', tone: 'risk-reduce', value: '07' },
          { label: 'Needs review', tone: 'risk-increase', value: '02' },
        ]}
      />

      <SectionCard
        title="AI-Ready Primitive Set"
        description="这组 primitive 是给开发者和 AI 共同使用的。"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <div className="qa-list-row">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-title-sm font-semibold text-ink">Plugin registry card</h2>
              <EventBadge tone="risk-reduce">Healthy</EventBadge>
            </div>
            <p className="mt-3 text-body-md text-muted-strong">
              使用 <span className="qa-inline-code">qa-panel</span>、<span className="qa-inline-code">EventBadge</span>、
              <span className="qa-inline-code">Button variant="primary"</span> 组合即可贴合现有规范。
            </p>
          </div>
          <div className="qa-list-row">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-title-sm font-semibold text-ink">Plugin review card</h2>
              <EventBadge tone="approval-expiring">Awaiting approval</EventBadge>
            </div>
            <p className="mt-3 text-body-md text-muted-strong">
              审批状态继续走 warning 语义，不再为插件模块单独引入橙色实现。
            </p>
          </div>
        </div>
      </SectionCard>
    </div>
  )
}
