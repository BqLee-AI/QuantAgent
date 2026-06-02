import { describe, expect, it } from 'vitest'

import type { EventAuditNode } from '../types'
import {
  formatScoreDelta,
  getEventAuditNodeGroup,
  hasHumanEventAuditNodes,
  hasSystemEventAuditNodes,
  sortEventAuditNodes,
} from './event-audit-node'

const systemNode: EventAuditNode = {
  action: 'decision_created',
  actor: { id: 'decision.engine', label: 'Decision Engine', type: 'system' },
  kind: 'decision.created',
  occurredAt: '2026-05-28T10:35:00+08:00',
  outcome: 'created',
  summary: '生成建议。',
}

const humanNode: EventAuditNode = {
  action: 'request_reanalysis',
  actor: { id: 'operator.lead', label: '操盘负责人', type: 'human' },
  kind: 'reanalysis.requested',
  occurredAt: '2026-05-28T10:42:00+08:00',
  outcome: 'queued',
  summary: '请求重分析。',
}

describe('event audit node utils', () => {
  it('sorts nodes by occurred time', () => {
    expect(sortEventAuditNodes([humanNode, systemNode]).map((node) => node.kind)).toEqual([
      'decision.created',
      'reanalysis.requested',
    ])
  })

  it('detects system and human node groups', () => {
    expect(getEventAuditNodeGroup(systemNode)).toBe('system')
    expect(getEventAuditNodeGroup(humanNode)).toBe('human')
    expect(hasSystemEventAuditNodes([humanNode, systemNode])).toBe(true)
    expect(hasHumanEventAuditNodes([systemNode])).toBe(false)
  })

  it('formats score deltas for suggestion changes', () => {
    expect(formatScoreDelta(5)).toBe('+5')
    expect(formatScoreDelta(-3)).toBe('-3')
    expect(formatScoreDelta(undefined)).toBe('暂无分数变化')
  })
})
