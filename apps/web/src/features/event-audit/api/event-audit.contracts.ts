export type EventAuditNodeKind =
  | 'analysis.scored'
  | 'approval.requested'
  | 'approval.resolved'
  | 'decision.changed'
  | 'decision.created'
  | 'event.state_changed'
  | 'industry.analysis.completed'
  | 'reanalysis.requested'
  | 'runtime.error_recorded'

export type EventAuditActorType = 'human' | 'system'

export type EventAuditAvailabilityState =
  | 'available'
  | 'degraded'
  | 'empty'
  | 'forbidden'
  | 'unavailable'

export interface EventAuditActorContract {
  id?: string
  label: string
  type: EventAuditActorType
}

export interface EventAuditSuggestionSnapshotContract {
  confidence?: number
  recommendationScore?: number
  summary: string
}

export interface EventAuditSuggestionChangeContract {
  after: EventAuditSuggestionSnapshotContract
  before: EventAuditSuggestionSnapshotContract
  reason: string
  scoreDelta?: number
}

export interface EventAuditNodeContract {
  actor: EventAuditActorContract
  action: string
  kind: EventAuditNodeKind
  occurredAt: string
  outcome: string
  requestId?: string
  runId?: string
  approvalId?: string
  summary: string
  suggestionChange?: EventAuditSuggestionChangeContract
  traceId?: string
}

export interface EventAuditAvailabilityContract {
  message: string
  state: EventAuditAvailabilityState
}

export interface EventAuditTimelineResponse {
  availability: EventAuditAvailabilityContract
  eventId: string
  nodes: EventAuditNodeContract[]
}
