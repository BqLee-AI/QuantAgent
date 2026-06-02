import { formatVerificationStatus } from '@/features/event-scoring/utils/event-scoring-labels'
import {
  DetailFacts,
  LinkButton,
  PageHeader,
  PageSectionCard,
  SectionHeader,
} from '@/shared/ui'

import { useEventAuditPage } from '../../hooks'
import { EventAuditErrorState, EventAuditLoadingState, EventAuditNotFoundState } from '../states/EventAuditStatePanel'
import { EventAuditTimeline } from '../timeline/EventAuditTimeline'

export function EventAuditPage({ eventId }: { eventId: string }) {
  const {
    event,
    isLoading,
    pageModel,
    queryError,
    refetch,
    relatedApproval,
    relatedRun,
  } = useEventAuditPage(eventId)

  if (!event) {
    return <EventAuditNotFoundState />
  }

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="事件级审计"
        title="事件时间线"
        description="按事件回放建议生成、建议变更、重分析和人工动作；本页不替代 Runtime 或全局日志。"
      />

      <PageSectionCard>
        <SectionHeader
          eyebrow="当前事件摘要"
          title={event.title}
          description="时间线围绕当前 Event 组织，帮助复核建议为什么变成现在这样。"
        />
        <DetailFacts
          rows={[
            `事件 ID：${event.id}`,
            `来源：${event.source}`,
            `当前状态：${event.status}`,
            `事件可信度：${event.score.eventReliability} / 100`,
            `验证状态：${formatVerificationStatus(event.score.verificationStatus)}`,
            `关联审批：${relatedApproval?.id ?? '暂无'}`,
            `关联运行：${relatedRun?.id ?? '暂无'}`,
          ]}
        />
        <div className="flex flex-wrap gap-2">
          <LinkButton to="/events/$eventId" params={{ eventId: event.id }} variant="outline">
            返回事件详情
          </LinkButton>
          {relatedApproval ? (
            <LinkButton to="/approvals/$approvalId" params={{ approvalId: relatedApproval.id }} variant="outline">
              查看审批详情
            </LinkButton>
          ) : null}
          {relatedRun ? (
            <LinkButton to="/runtime/agents/$runId" params={{ runId: relatedRun.id }} variant="outline">
              查看运行详情
            </LinkButton>
          ) : null}
        </div>
      </PageSectionCard>

      {isLoading ? <EventAuditLoadingState /> : null}

      {queryError ? (
        <EventAuditErrorState
          message={pageModel.availability.message}
          onRetry={() => void refetch()}
          requestId={queryError.requestId}
          traceId={queryError.traceId}
        />
      ) : null}

      <PageSectionCard>
        <SectionHeader
          eyebrow="时间线节点"
          title={`事件 ${pageModel.eventId} 的关键节点`}
          description={pageModel.source === 'mock-fallback'
            ? `${pageModel.availability.message} 这些内容是占位数据，不代表真实后端审计记录。`
            : pageModel.availability.message}
        />
        <EventAuditTimeline emptyMessage={pageModel.availability.message} nodes={pageModel.nodes} />
      </PageSectionCard>
    </div>
  )
}
