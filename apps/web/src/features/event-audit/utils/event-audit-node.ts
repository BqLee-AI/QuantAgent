import type { EventAuditNode, EventAuditNodeFilter, EventAuditNodeGroup } from '../types'

const systemKinds = new Set<EventAuditNode['kind']>([
  'analysis.scored',
  'decision.changed',
  'decision.created',
  'event.state_changed',
  'industry.analysis.completed',
  'runtime.error_recorded',
])

export function sortEventAuditNodes(nodes: readonly EventAuditNode[]): EventAuditNode[] {
  return [...nodes].sort((left, right) => {
    return new Date(right.occurredAt).getTime() - new Date(left.occurredAt).getTime()
  })
}

export function getEventAuditNodeGroup(node: EventAuditNode): EventAuditNodeGroup {
  if (node.actor.type === 'human') {
    return 'human'
  }

  return systemKinds.has(node.kind) ? 'system' : 'system'
}

export function hasHumanEventAuditNodes(nodes: readonly EventAuditNode[]): boolean {
  return nodes.some((node) => getEventAuditNodeGroup(node) === 'human')
}

export function hasSystemEventAuditNodes(nodes: readonly EventAuditNode[]): boolean {
  return nodes.some((node) => getEventAuditNodeGroup(node) === 'system')
}

export function filterEventAuditNodes(
  nodes: readonly EventAuditNode[],
  filter: EventAuditNodeFilter,
): EventAuditNode[] {
  if (filter === 'all') {
    return [...nodes]
  }

  return nodes.filter((node) => {
    if (filter === 'changes') {
      return node.suggestionChange !== undefined
    }

    if (filter === 'reanalysis') {
      return node.kind === 'reanalysis.requested'
    }

    return getEventAuditNodeGroup(node) === filter
  })
}

export function findLatestSuggestionChangeNode(nodes: readonly EventAuditNode[]): EventAuditNode | null {
  return sortEventAuditNodes(nodes).find((node) => node.suggestionChange !== undefined) ?? null
}

export function countSuggestionChangeNodes(nodes: readonly EventAuditNode[]): number {
  return nodes.filter((node) => node.suggestionChange !== undefined).length
}

export function countReanalysisNodes(nodes: readonly EventAuditNode[]): number {
  return nodes.filter((node) => node.kind === 'reanalysis.requested').length
}

export function formatEventAuditNodeTime(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

export function formatScoreDelta(value: number | undefined): string {
  if (value === undefined) {
    return '暂无分数变化'
  }

  if (value > 0) {
    return `+${value}`
  }

  return String(value)
}

export function formatEventAuditOutcome(value: string): string {
  const outcomeLabels: Record<string, string> = {
    'analysis completed': '分析完成',
    'amended summary': '已修改摘要',
    'awaiting verification': '等待验证',
    'captured -> analyzing': '进入分析',
    'captured -> routed': '已路由',
    'manual review requested': '已请求人工复核',
    'reanalysis queued': '重分析排队',
    'recommendation created': '建议已生成',
    'recommendation updated': '建议已更新',
    'strong_confirm required': '需要强确认',
  }

  return outcomeLabels[value] ?? value
}
