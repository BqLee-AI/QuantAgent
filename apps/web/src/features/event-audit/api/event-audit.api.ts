import { BaseApi, type ApiClient } from '@/shared/api'

import type { EventAuditTimelineResponse } from './event-audit.contracts'

export class EventAuditApi extends BaseApi {
  constructor(apiClient: ApiClient) {
    super(apiClient, { basePath: '/events' })
  }

  getEventAuditTimeline(eventId: string): Promise<EventAuditTimelineResponse> {
    return this.get<EventAuditTimelineResponse>(`/${encodeURIComponent(eventId)}/audit`)
  }
}

export function createEventAuditApi(apiClient: ApiClient): EventAuditApi {
  return new EventAuditApi(apiClient)
}
