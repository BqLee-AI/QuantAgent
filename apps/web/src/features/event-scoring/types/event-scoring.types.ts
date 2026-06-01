export type EventScoreLevel = 'A' | 'B' | 'C' | 'S'

export type VerificationStatus =
  | 'single_source'
  | 'dual_verified'
  | 'conflicting_sources'
  | 'awaiting_verification'
  | 'invalid_output'

export type AnalysisStatus =
  | 'captured'
  | 'analyzing'
  | 'decision_ready'
  | 'pending_approval'
  | 'warning'
  | 'analysis_failed'
  | 'policy_blocked'

export type RecommendationPriority =
  | 'high'
  | 'medium'
  | 'review'

export interface EventScoreSummary {
  sourceAuthority: EventScoreLevel
  eventReliability: number
  impactStrength: number
  freshness: 'high' | 'medium' | 'low'
  eventPriority: number
  priorityBand: EventScoreLevel
  verificationStatus: VerificationStatus
  analysisConfidence: number
  recommendationScore: number
  uncertaintySummary: string
  selectionReason: string
}

export type EventDegradationKind =
  | 'weak_source'
  | 'conflicting_sources'
  | 'tool_failure'
  | 'invalid_analysis'
  | 'stale_event'
  | 'policy_blocked'

export interface EventDegradationNotice {
  kind: EventDegradationKind
  title: string
  summary: string
  requestId?: string
  traceId?: string
}

export interface EventScoreCardModel {
  id: string
  title: string
  source: string
  sourceType: string
  publishedAt: string
  publishedMinutesAgo: number
  status: AnalysisStatus
  summary: string
  actionHint: string
  industries: string[]
  impactDirection: string
  score: EventScoreSummary
  degradationNotices: readonly EventDegradationNotice[]
  analysisHighlights?: {
    support: string
    opposition: string
    verificationNote?: string
  }
}

export interface ApprovalScoreContext {
  recommendationPriority: RecommendationPriority
  recommendationScore: number
  eventReliabilitySummary: number
  analysisConfidenceSummary: number
  riskDirection: string
  riskLevel: string
  confirmationLevel: string
  expiresIn: string
  expirationAction: string
}

export interface ApprovalScoreCardModel {
  id: string
  eventId: string
  eventTitle: string
  actionLabel: string
  triggerSummary: string
  scoreContext: ApprovalScoreContext
  degradationNotices: readonly EventDegradationNotice[]
}
