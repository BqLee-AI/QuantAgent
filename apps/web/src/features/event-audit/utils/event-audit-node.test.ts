import { describe, expect, it } from 'vitest'

import type { EventAuditNode } from '../types'
import {
  formatScoreDelta,
  formatEventAuditOutcome,
  filterEventAuditNodes,
  findLatestSuggestionChangeNode,
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

const changeNode: EventAuditNode = {
  action: 'decision_changed',
  actor: { id: 'decision.engine', label: 'Decision Engine', type: 'system' },
  kind: 'decision.changed',
  occurredAt: '2026-05-28T10:49:00+08:00',
  outcome: 'updated',
  summary: '重分析后调整建议。',
  suggestionChange: {
    after: { summary: '维持降低风险暴露。' },
    before: { summary: '降低风险暴露但信号未验证。' },
    reason: '补充验证后未发现缓释信号。',
    scoreDelta: 5,
  },
}

describe('event audit node utils', () => {
  it('sorts nodes by occurred time with latest first', () => {
    expect(sortEventAuditNodes([humanNode, systemNode]).map((node) => node.kind)).toEqual([
      'reanalysis.requested',
      'decision.created',
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

  it('formats backend outcomes for Chinese-first UI', () => {
    expect(formatEventAuditOutcome('recommendation updated')).toBe('建议已更新')
    expect(formatEventAuditOutcome('strong_confirm required')).toBe('需要强确认')
    expect(formatEventAuditOutcome('custom outcome')).toBe('custom outcome')
  })

  it('filters nodes by review intent', () => {
    const nodes = [systemNode, humanNode, changeNode]

    expect(filterEventAuditNodes(nodes, 'changes')).toEqual([changeNode])
    expect(filterEventAuditNodes(nodes, 'human')).toEqual([humanNode])
    expect(filterEventAuditNodes(nodes, 'reanalysis')).toEqual([humanNode])
  })

  it('finds the latest suggestion change node', () => {
    expect(findLatestSuggestionChangeNode([changeNode, systemNode])).toBe(changeNode)
    expect(findLatestSuggestionChangeNode([systemNode, humanNode])).toBeNull()
  })
})
