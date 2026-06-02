import type { EventAuditNode, EventAuditNodeGroup } from '../types'

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
    return new Date(left.occurredAt).getTime() - new Date(right.occurredAt).getTime()
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
