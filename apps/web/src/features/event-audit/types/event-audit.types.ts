import type {
  EventAuditActorContract,
  EventAuditAvailabilityContract,
  EventAuditNodeContract,
  EventAuditNodeKind,
  EventAuditSuggestionChangeContract,
} from '../api'

export type EventAuditActor = EventAuditActorContract
export type EventAuditAvailability = EventAuditAvailabilityContract
export type EventAuditNode = EventAuditNodeContract
export type EventAuditSuggestionChange = EventAuditSuggestionChangeContract
export type { EventAuditNodeKind }

export type EventAuditNodeGroup = 'human' | 'system'
export type EventAuditNodeFilter = 'all' | 'changes' | 'human' | 'reanalysis' | 'system'

export interface EventAuditPageModel {
  availability: EventAuditAvailability
  eventId: string
  nodes: EventAuditNode[]
  source: 'api' | 'mock-fallback'
}
