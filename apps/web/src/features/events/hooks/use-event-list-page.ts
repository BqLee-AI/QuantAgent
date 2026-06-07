import { useEventFilters } from './use-event-filters';

import { useEventIndustryOptionsQuery, useEventListQuery } from '../queries';

export function useEventListPage() {
  const filters = useEventFilters();
  const eventsQuery = useEventListQuery(filters.params);
  const industryOptionsQuery = useEventIndustryOptionsQuery();

  return {
    eventsQuery,
    filters,
    industryOptions: industryOptionsQuery.data ?? [],
    industryOptionsQuery,
  };
}
