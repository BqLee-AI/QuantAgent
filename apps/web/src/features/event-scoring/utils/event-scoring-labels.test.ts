import {
  describe,
  expect,
  it,
} from 'vitest'

import {
  formatEventReliability,
  formatFreshnessLabel,
  formatRecommendationPriority,
  formatDegradationTone,
  formatVerificationStatus,
} from './event-scoring-labels'

describe('event scoring labels', () => {
  it('formats verification status labels', () => {
    expect(formatVerificationStatus('dual_verified')).toBe('双信源验证')
    expect(formatVerificationStatus('conflicting_sources')).toBe('多信源冲突')
    expect(formatVerificationStatus('invalid_output')).toBe('分析无效')
  })

  it('formats score and freshness labels', () => {
    expect(formatEventReliability(82)).toContain('82 / 100')
    expect(formatFreshnessLabel('high')).toBe('时效性 高')
  })

  it('formats recommendation priorities', () => {
    expect(formatRecommendationPriority('high')).toBe('高优先级')
    expect(formatRecommendationPriority('review')).toBe('复核优先')
  })

  it('maps degradation kinds to tones', () => {
    expect(formatDegradationTone('policy_blocked')).toBe('danger')
    expect(formatDegradationTone('tool_failure')).toBe('warning')
    expect(formatDegradationTone('stale_event')).toBe('muted')
  })
})
