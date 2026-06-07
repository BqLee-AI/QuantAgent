import { BaseApi, type ApiClient } from '@/shared/api';

import type {
  EventsApiContract,
  EventDetailResponse,
  EventListResponse,
  EventQueryParams,
  EventRouterOutputResponse,
} from './events.contracts';

export class EventsApi extends BaseApi implements EventsApiContract {
  constructor(apiClient: ApiClient) {
    super(apiClient, { basePath: '/events' });
  }

  listEvents(params: EventQueryParams = {}): Promise<EventListResponse> {
    return this.get<EventListResponse>('', { params: { ...params } });
  }

  getEventDetail(rawEventId: string): Promise<EventDetailResponse> {
    return this.get<EventDetailResponse>(`/${encodeURIComponent(rawEventId)}`);
  }

  getRouterOutput(rawEventId: string, routedEventId?: string | null): Promise<EventRouterOutputResponse> {
    return this.get<EventRouterOutputResponse>(`/${encodeURIComponent(rawEventId)}/router-output`, {
      params: { routed_event_id: routedEventId ?? undefined },
    });
  }
}

export function createEventsApi(apiClient: ApiClient): EventsApi {
  return new EventsApi(apiClient);
}
