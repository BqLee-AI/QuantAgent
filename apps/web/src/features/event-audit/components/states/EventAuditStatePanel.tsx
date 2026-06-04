import { LinkButton, PageSectionCard, SectionHeader } from '@/shared/ui'

export function EventAuditNotFoundState() {
  return (
    <div className="grid gap-5">
      <section className="page-header">
        <p className="page-kicker">事件级审计</p>
        <h1 className="page-title">事件不存在</h1>
      </section>
      <PageSectionCard>
        <SectionHeader
          eyebrow="未找到"
          title="没有匹配事件"
        />
        <div className="flex flex-wrap gap-2">
          <LinkButton to="/events" variant="outline">返回事件中心</LinkButton>
        </div>
      </PageSectionCard>
    </div>
  )
}

export function EventAuditLoadingState() {
  return (
    <PageSectionCard>
      <SectionHeader
        eyebrow="读取中"
        title="正在读取"
      />
    </PageSectionCard>
  )
}
