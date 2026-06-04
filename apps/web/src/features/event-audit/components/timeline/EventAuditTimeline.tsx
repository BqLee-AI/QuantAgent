import { Chip } from '@heroui/react'
import { twMerge } from 'tailwind-merge'

import type { EventAuditNode } from '../../types'
import {
  formatEventAuditNodeTime,
  formatEventAuditOutcome,
  formatScoreDelta,
  getEventAuditNodeGroup,
} from '../../utils'

const subtleChipClass = 'bg-surface-soft text-body-sm font-bold text-muted-strong'
const humanChipClass = 'bg-warning/10 text-body-sm font-bold text-warning'
const scoreChipClass = 'bg-primary/10 text-body-sm font-bold text-primary'

function getNodeTitle(node: EventAuditNode): string {
  if (node.suggestionChange) {
    return '建议变化'
  }

  if (node.kind === 'reanalysis.requested') {
    return '请求重分析'
  }

  if (node.kind === 'approval.requested') {
    return '进入审批'
  }

  if (node.kind === 'approval.resolved') {
    return '人工处理'
  }

  if (node.kind === 'industry.analysis.completed' || node.kind === 'analysis.scored') {
    return '完成分析'
  }

  if (node.kind === 'event.state_changed') {
    return '事件状态变化'
  }

  return formatEventAuditOutcome(node.outcome)
}

function EventAuditNodeArticle({ node }: { node: EventAuditNode }) {
  const group = getEventAuditNodeGroup(node)
  const accentClass = group === 'human' ? 'border-warning/40 bg-warning/5' : 'border-hairline bg-surface'
  const actorLabel = group === 'human' ? '人工' : node.actor.label

  return (
    <article className={`group overflow-hidden rounded-3xl border shadow-[0_10px_28px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-[0_18px_42px_rgba(15,23,42,0.08)] ${accentClass}`}>
      <div className="grid gap-3 p-4 xl:grid-cols-[minmax(0,1fr)_220px] xl:items-start">
        <div className="grid gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Chip className={twMerge(subtleChipClass)} size="sm" variant="soft">
              {formatEventAuditNodeTime(node.occurredAt)}
            </Chip>
            <Chip className={twMerge(group === 'human' ? humanChipClass : subtleChipClass)} size="sm" variant="soft">
              {actorLabel}
            </Chip>
            {node.suggestionChange ? (
              <Chip className={twMerge(scoreChipClass)} size="sm" variant="soft">
                {formatScoreDelta(node.suggestionChange.scoreDelta)}
              </Chip>
            ) : null}
          </div>

          <div className="grid min-w-0 gap-1.5">
            <h3 className="m-0 wrap-anywhere text-title-sm font-extrabold leading-tight text-foreground group-hover:text-primary">
              {getNodeTitle(node)}
            </h3>
            <p className="m-0 text-body-sm leading-[1.55] text-muted">{node.summary}</p>
          </div>
        </div>

        <div className="grid gap-2 rounded-2xl bg-canvas p-3">
          <div className="rounded-2xl bg-surface px-3 py-2 text-body-sm font-extrabold text-muted-strong">
            {formatEventAuditOutcome(node.outcome)}
          </div>
          <div className="rounded-2xl bg-surface px-3 py-2 text-[12px] font-bold text-muted">
            {actorLabel}
          </div>
        </div>
      </div>

      {node.suggestionChange ? (
        <div className="grid gap-2 border-t border-hairline bg-canvas/70 p-4 pt-3 md:grid-cols-2">
          <ChangeBlock label="变更前" text={node.suggestionChange.before.summary} />
          <ChangeBlock label="变更后" text={node.suggestionChange.after.summary} />
        </div>
      ) : null}
    </article>
  )
}

function ChangeBlock({
  label,
  text,
}: {
  label: string
  text: string
}) {
  return (
    <div className="rounded-2xl bg-surface px-3 py-2">
      <p className="m-0 text-[12px] font-extrabold text-muted">{label}</p>
      <p className="m-0 mt-1 text-body-sm leading-[1.5] text-muted-strong">{text}</p>
    </div>
  )
}

export function EventAuditTimeline({
  emptyMessage = '当前事件暂无审计记录。',
  nodes,
}: {
  emptyMessage?: string
  nodes: readonly EventAuditNode[]
}) {
  if (nodes.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-hairline-strong bg-surface p-4">
        <p className="m-0 text-body-sm text-muted">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="grid gap-3">
      {nodes.map((node) => (
        <EventAuditNodeArticle key={`${node.kind}-${node.occurredAt}-${node.action}`} node={node} />
      ))}
    </div>
  )
}
