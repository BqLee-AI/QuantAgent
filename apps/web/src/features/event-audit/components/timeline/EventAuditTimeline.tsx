import type { EventAuditNode } from '../../types'
import {
  formatEventAuditNodeTime,
  formatScoreDelta,
  getEventAuditNodeGroup,
  hasHumanEventAuditNodes,
  hasSystemEventAuditNodes,
} from '../../utils'

function EventAuditNodeArticle({ node }: { node: EventAuditNode }) {
  const group = getEventAuditNodeGroup(node)
  const borderClass = group === 'human' ? 'border-warning' : 'border-hairline-strong'

  return (
    <article className={`grid gap-2 border-l-2 ${borderClass} pl-3.5`}>
      <div className="flex flex-wrap items-center gap-2">
        <p className="m-0 text-[12px] font-bold text-muted">
          {formatEventAuditNodeTime(node.occurredAt)} · {node.kind}
        </p>
        <span className="rounded-full bg-surface px-2 py-0.5 text-[12px] font-bold text-muted-strong">
          {group === 'human' ? '人工节点' : '系统节点'}
        </span>
      </div>
      <h3 className="m-0 wrap-anywhere text-title-sm font-bold text-ink">
        {node.action} · {node.outcome}
      </h3>
      <p className="m-0 text-body-sm leading-[1.55] text-muted">{node.summary}</p>
      <div className="grid gap-1 text-body-sm text-muted">
        <p className="m-0">actor：{node.actor.label}{node.actor.id ? `（${node.actor.id}）` : ''}</p>
        {node.requestId ? <p className="m-0">request_id：{node.requestId}</p> : null}
        {node.traceId ? <p className="m-0">trace_id：{node.traceId}</p> : <p className="m-0">trace_id：当前节点未提供，不阻断时间线。</p>}
      </div>
      {node.suggestionChange ? (
        <div className="grid gap-2 rounded-lg border border-hairline bg-surface p-3">
          <p className="m-0 text-body-sm font-bold text-ink">建议变化摘要</p>
          <p className="m-0 text-body-sm text-muted">变更前：{node.suggestionChange.before.summary}</p>
          <p className="m-0 text-body-sm text-muted">变更后：{node.suggestionChange.after.summary}</p>
          <p className="m-0 text-body-sm text-muted">原因：{node.suggestionChange.reason}</p>
          <p className="m-0 text-body-sm text-muted">推荐度变化：{formatScoreDelta(node.suggestionChange.scoreDelta)}</p>
        </div>
      ) : null}
    </article>
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

  const hasHuman = hasHumanEventAuditNodes(nodes)
  const hasSystem = hasSystemEventAuditNodes(nodes)

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap gap-2">
        <span className="rounded-full bg-surface px-3 py-1 text-body-sm font-bold text-muted-strong">
          {hasSystem ? '包含系统节点' : '无系统节点'}
        </span>
        <span className="rounded-full bg-surface px-3 py-1 text-body-sm font-bold text-muted-strong">
          {hasHuman ? '包含人工节点' : '无人工节点'}
        </span>
      </div>
      <div className="grid gap-3">
        {nodes.map((node) => (
          <EventAuditNodeArticle key={`${node.kind}-${node.occurredAt}-${node.action}`} node={node} />
        ))}
      </div>
    </div>
  )
}
