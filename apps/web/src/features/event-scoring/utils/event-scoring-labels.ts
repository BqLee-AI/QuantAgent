import type {
  EventDegradationKind,
  EventScoreLevel,
  EventScoreSummary,
  RecommendationPriority,
  VerificationStatus,
} from '../types/event-scoring.types'

function formatScoreBand(score: number) {
  if (score >= 85) {
    return '高'
  }

  if (score >= 70) {
    return '中高'
  }

  if (score >= 55) {
    return '中'
  }

  return '低'
}

export function formatSourceAuthority(level: EventScoreLevel) {
  return `来源权威度 ${level}`
}

export function formatEventReliability(score: number) {
  return `事件可信度 ${score} / 100 · ${formatScoreBand(score)}`
}

export function formatImpactStrength(score: number) {
  return `行业影响 ${score} / 100 · ${formatScoreBand(score)}`
}

export function formatFreshnessLabel(freshness: EventScoreSummary['freshness']) {
  if (freshness === 'high') {
    return '时效性 高'
  }

  if (freshness === 'medium') {
    return '时效性 中'
  }

  return '时效性 低'
}

export function formatPriorityLabel(score: number, band: EventScoreLevel) {
  return `事件优先级 ${score} / 100 · ${band}`
}

export function formatVerificationStatus(status: VerificationStatus) {
  switch (status) {
    case 'dual_verified':
      return '双信源验证'
    case 'conflicting_sources':
      return '多信源冲突'
    case 'awaiting_verification':
      return '待验证'
    case 'invalid_output':
      return '分析无效'
    case 'single_source':
    default:
      return '单信源'
  }
}

export function formatRecommendationPriority(priority: RecommendationPriority) {
  switch (priority) {
    case 'high':
      return '高优先级'
    case 'review':
      return '复核优先'
    case 'medium':
    default:
      return '中优先级'
  }
}

export function formatDegradationTone(kind: EventDegradationKind) {
  switch (kind) {
    case 'policy_blocked':
    case 'invalid_analysis':
      return 'danger'
    case 'conflicting_sources':
    case 'tool_failure':
      return 'warning'
    case 'stale_event':
      return 'muted'
    case 'weak_source':
    default:
      return 'neutral'
  }
}
