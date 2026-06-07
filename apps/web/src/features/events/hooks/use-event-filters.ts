import { useState } from 'react';

import type { EventDecision, EventQueryParams, EventSort } from '../types';

export interface EventFilterState {
  industry: string;
  keyword: string;
  sort: EventSort;
  time: 'all-time' | 'last-24h' | 'last-3d' | 'last-3h' | 'last-7d';
  decision: EventDecision | 'all' | '';
}

export function useEventFilters() {
  const [filters, setFilters] = useState<EventFilterState>({
    keyword: '',
    industry: 'all-industries',
    sort: 'routed_at_desc',
    time: 'last-24h',
    decision: '',
  });

  const params: EventQueryParams = {
    keyword: filters.keyword || undefined,
    decision: decisionFromFilters(filters),
    industry_id: industryIdFromFilter(filters.industry),
    sort: filters.sort,
    time_from: timeFromFilter(filters.time),
    limit: 50,
  };

  return {
    filters,
    params,
    setDecision(decision: EventFilterState['decision']) {
      setFilters((current) => ({ ...current, decision }));
    },
    setIndustry(industry: EventFilterState['industry']) {
      setFilters((current) => ({ ...current, industry }));
    },
    setKeyword(keyword: string) {
      setFilters((current) => ({ ...current, keyword }));
    },
    setSort(sort: EventFilterState['sort']) {
      setFilters((current) => ({ ...current, sort }));
    },
    setTime(time: EventFilterState['time']) {
      setFilters((current) => ({ ...current, time }));
    },
  };
}

function decisionFromFilters(filters: EventFilterState): EventQueryParams['decision'] {
  if (filters.decision) return filters.decision;
  return undefined;
}

function industryIdFromFilter(industry: EventFilterState['industry']): string | undefined {
  if (industry === 'all-industries') return undefined;
  return industry;
}

function timeFromFilter(time: EventFilterState['time']): string | undefined {
  if (time === 'all-time') return undefined;
  const now = Date.now();
  const deltaMsByFilter: Record<Exclude<EventFilterState['time'], 'all-time'>, number> = {
    'last-3h': 3 * 60 * 60 * 1000,
    'last-24h': 24 * 60 * 60 * 1000,
    'last-3d': 3 * 24 * 60 * 60 * 1000,
    'last-7d': 7 * 24 * 60 * 60 * 1000,
  };
  const deltaMs = deltaMsByFilter[time];
  return new Date(now - deltaMs).toISOString();
}
