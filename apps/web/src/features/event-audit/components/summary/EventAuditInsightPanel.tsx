import { Chip } from '@heroui/react'
import { twMerge } from 'tailwind-merge'

import {
  LinkButton,
  PageSectionCard,
} from '@/shared/ui'

import type { EventAuditNode } from '../../types'
import {
  countReanalysisNodes,
  countSuggestionChangeNodes,
  findLatestSuggestionChangeNode,
  formatScoreDelta,
} from '../../utils'

const chipClass = 'bg-surface-soft text-body-sm font-bold text-muted-strong'
const signalClass = 'bg-primary/10 text-body-sm font-bold text-primary'

export function EventAuditInsightPanel({
  eventReliability,
  eventId,
  eventTitle,
  isLoading,
  nodes,
  onRetry,
  relatedApprovalId,
  relatedRunId,
  requestId,
  source,
  statusMessage,
  traceId,
  verificationLabel,
}: {
  eventReliability: number
  eventId: string
  eventTitle: string
  isLoading: boolean
  nodes: readonly EventAuditNode[]
  onRetry?: () => void
  relatedApprovalId?: string
  relatedRunId?: string
  requestId?: string
  source: 'api' | 'mock-fallback'
  statusMessage: string
  traceId?: string
  verificationLabel: string
}) {
  const latestChangeNode = findLatestSuggestionChangeNode(nodes)
  const latestChange = latestChangeNode?.suggestionChange
  const changeCount = countSuggestionChangeNodes(nodes)
  const reanalysisCount = countReanalysisNodes(nodes)
  const humanCount = nodes.filter((node) => node.actor.type === 'human').length

  return (
    <PageSectionCard className="border-primary/20 bg-surface">
      <div className="grid gap-3 rounded-2xl border border-hairline bg-canvas p-4">
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-start">
          <div className="grid gap-1">
            <p className="m-0 text-[12px] font-extrabold uppercase tracking-[0.04em] text-muted">审计结论</p>
            <p className="m-0 wrap-anywhere text-title-md font-bold text-ink">
              {latestChange ? '建议已变化' : '无建议变化记录'}
            </p>
            <p className="m-0 text-body-sm text-muted">
              {eventTitle} · 可信度 {eventReliability} / 100 · {verificationLabel}
            </p>
          </div>

          <div className="flex flex-wrap gap-2 xl:justify-end">
            <LinkButton to="/events/$eventId" params={{ eventId }} variant="outline">
              回事件详情
            </LinkButton>
            {relatedApprovalId ? (
              <LinkButton to="/approvals/$approvalId" params={{ approvalId: relatedApprovalId }} variant="outline">
                看审批上下文
              </LinkButton>
            ) : null}
            {relatedRunId ? (
              <LinkButton to="/runtime/agents/$runId" params={{ runId: relatedRunId }} variant="outline">
                看运行详情
              </LinkButton>
            ) : null}
          </div>
        </div>

        <div className="grid gap-3">
          <div className="flex flex-wrap gap-2">
            <Chip className={twMerge(signalClass)} size="sm" variant="soft">
              建议变化 {changeCount}
            </Chip>
            <Chip className={twMerge(chipClass)} size="sm" variant="soft">
              重分析 {reanalysisCount}
            </Chip>
            <Chip className={twMerge(chipClass)} size="sm" variant="soft">
              人工动作 {humanCount}
            </Chip>
            <Chip className={twMerge(source === 'mock-fallback' ? 'bg-warning/10 text-warning' : chipClass)} size="sm" variant="soft">
              {source === 'mock-fallback' ? '占位数据' : '后端审计'}
            </Chip>
            {isLoading ? (
              <Chip className={twMerge(chipClass)} size="sm" variant="soft">
                读取中
              </Chip>
            ) : null}
          </div>

          {source === 'mock-fallback' || requestId || traceId ? (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-2xl border border-hairline bg-surface px-3 py-1.5 text-[12px] font-bold text-muted">
              <span>{statusMessage}</span>
              {requestId ? <span>Request ID: {requestId}</span> : null}
              {traceId ? <span>Trace ID: {traceId}</span> : null}
              {onRetry ? (
                <button
                  className="text-[12px] font-bold text-primary"
                  type="button"
                  onClick={onRetry}
                >
                  重新读取
                </button>
              ) : null}
            </div>
          ) : null}

          {latestChange ? (
            <div className="grid gap-2">
              <p className="m-0 text-title-sm font-bold text-ink">{latestChange.reason}</p>
              <div className="grid gap-2 md:grid-cols-2">
                <ChangeSnapshot label="变更前" text={latestChange.before.summary} />
                <ChangeSnapshot label="变更后" text={latestChange.after.summary} />
              </div>
              <p className="m-0 text-body-sm font-bold text-muted-strong">
                推荐度变化：{formatScoreDelta(latestChange.scoreDelta)}
              </p>
            </div>
          ) : (
            <p className="m-0 text-body-sm leading-[1.55] text-muted">
              暂无 before / after。
            </p>
          )}
        </div>
      </div>
    </PageSectionCard>
  )
}

function ChangeSnapshot({
  label,
  text,
}: {
  label: string
  text: string
}) {
  return (
    <div className="rounded-2xl border border-hairline bg-surface px-3 py-2">
      <p className="m-0 text-[12px] font-bold text-muted">{label}</p>
      <p className="m-0 mt-1 text-body-sm leading-[1.5] text-muted-strong">{text}</p>
    </div>
  )
}
