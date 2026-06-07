import type {
  EventDetailResponse,
  EventListResponse,
  EventQueryParams,
  EventRouterOutputResponse,
} from '../types';

export interface EventsApiContract {
  listEvents(params?: EventQueryParams): Promise<EventListResponse>;
  getEventDetail(rawEventId: string): Promise<EventDetailResponse>;
  getRouterOutput(rawEventId: string, routedEventId?: string | null): Promise<EventRouterOutputResponse>;
}

export type {
  EventDetailResponse,
  EventListResponse,
  EventQueryParams,
  EventRouterOutputResponse,
};
