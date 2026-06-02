import { Button } from '@heroui/react'

import { LinkButton, PageSectionCard, SectionHeader } from '@/shared/ui'

export function EventAuditNotFoundState() {
  return (
    <div className="grid gap-5">
      <section className="page-header">
        <p className="page-kicker">事件级审计</p>
        <h1 className="page-title">事件不存在</h1>
        <p className="page-description">当前事件 ID 没有匹配到可展示事件，请返回事件中心重新选择。</p>
      </section>
      <PageSectionCard>
        <SectionHeader
          eyebrow="未找到"
          title="不会静默兜底到其他事件"
          description="审计页主对象是当前 Event，不能把未知 ID 回放到其他事件链路。"
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
        title="正在读取事件审计时间线"
        description="页面会优先读取后端事件审计快照；接口未接通时才展示明确标识的占位数据。"
      />
    </PageSectionCard>
  )
}

export function EventAuditErrorState({
  message,
  onRetry,
  requestId,
  traceId,
}: {
  message: string
  onRetry: () => void
  requestId?: string
  traceId?: string
}) {
  return (
    <PageSectionCard>
      <SectionHeader
        eyebrow="读取失败"
        title="后端事件审计接口不可用"
        description={message}
        action={<Button size="sm" variant="outline" onPress={onRetry}>重试</Button>}
      />
      <div className="grid gap-2">
        {requestId ? <p className="m-0 text-body-sm text-muted">Request ID：{requestId}</p> : null}
        {traceId ? <p className="m-0 text-body-sm text-muted">Trace ID：{traceId}</p> : null}
      </div>
    </PageSectionCard>
  )
}
