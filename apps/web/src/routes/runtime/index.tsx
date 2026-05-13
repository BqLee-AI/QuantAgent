import { Button } from '@heroui/react'
import { createFileRoute } from '@tanstack/react-router'
import { MetricCard, PageHero, SectionCard } from '@/shared/ui/theme-primitives'

export const Route = createFileRoute('/runtime/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('runtime:read')) throw redirect({ to: '/' })
  },
  component: RuntimePage,
})

function RuntimePage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Runtime"
        title="Elevation 通过统一 shadow token 控制，而不是页面内联样式"
        description="卡片保持 DESIGN 要求的平面风格；需要浮层时走 modal 阴影 token。这样后续扩展 Drawer、Modal、Popover 时不会重新发明视觉层级。"
        actions={
          <>
            <Button variant="secondary">Pause Executor</Button>
            <Button variant="primary">Open Runtime</Button>
          </>
        }
        stats={[
          { label: 'Workers online', value: '11' },
          { label: 'Healthy queues', tone: 'risk-reduce', value: '05' },
          { label: 'Guarded flows', tone: 'approval-expiring', value: '02' },
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard
          title="Card Elevation"
          description="普通业务卡片仍然保持 flat + hairline 的 DESIGN 语言。"
        >
          <MetricCard label="Shadow token" value="shadow-card" />
        </SectionCard>

        <SectionCard
          title="Modal Elevation"
          description="需要浮层时统一进入 overlay 阴影，而不是局部写 box-shadow。"
        >
          <div className="qa-panel-modal p-5">
            <div className="qa-list-kicker">Overlay surface</div>
            <div className="mt-2 text-title-sm font-semibold text-ink">shadow-modal</div>
            <p className="mt-2 text-body-md text-muted-strong">
              HeroUI overlay 变量已经桥接到同一套 elevation token。
            </p>
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
