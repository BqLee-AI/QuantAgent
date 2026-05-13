import { Button, Input } from '@heroui/react'
import { createFileRoute } from '@tanstack/react-router'
import { PageHero, SectionCard } from '@/shared/ui/theme-primitives'

export const Route = createFileRoute('/settings/')({
  beforeLoad: () => {
    // TODO: Capability check placeholder
    // if (!hasCapability('settings:read')) throw redirect({ to: '/' })
  },
  component: SettingsPage,
})

function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Settings"
        title="设计规范已映射为可维护的主题层"
        description="修改 CSS 变量即可推动 Tailwind utility 与 HeroUI semantic 组件同步变化。这里保留一段 AI 可直接模仿的结构示例。"
        actions={
          <>
            <Input
              aria-label="Theme token search"
              className="w-full sm:w-[280px]"
              placeholder="Search token"
              variant="secondary"
            />
            <Button variant="primary">Apply Theme Change</Button>
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <SectionCard
          title="Theme Pipeline"
          description="显式保留 DESIGN → CSS variable → Tailwind/HeroUI 的映射链。"
        >
          <div className="space-y-3 text-body-md">
            <div className="qa-token-row">
              <span className="font-semibold text-ink">Primary CTA</span>
              <code className="qa-code">DESIGN primary → --qa-color-primary → bg-primary → HeroUI accent</code>
            </div>
            <div className="qa-token-row">
              <span className="font-semibold text-ink">Approval Warning</span>
              <code className="qa-code">DESIGN approval-expiring → --qa-color-approval-expiring → text-approval-expiring → HeroUI warning</code>
            </div>
            <div className="qa-token-row">
              <span className="font-semibold text-ink">Elevation</span>
              <code className="qa-code">DESIGN flat card / overlay modal → shadow-card / shadow-modal</code>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title="AI Composition Example"
          description="新组件优先组合这些 class，而不是回退到零散色值。"
        >
          <pre className="qa-code-block">{`<section className="qa-panel p-6">
  <h2 className="text-title-md font-semibold text-ink">Approval queue</h2>
  <p className="mt-2 text-body-md text-muted">Uses shared token wiring.</p>
  <EventBadge tone="approval-expiring">12m left</EventBadge>
  <Button variant="primary">Confirm</Button>
</section>`}</pre>
        </SectionCard>
      </div>
    </div>
  )
}
