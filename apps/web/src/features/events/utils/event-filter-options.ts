import type { EventFilterGroup, EventFilterOption } from '../types';
import type { EventFilterState } from '../hooks/use-event-filters';

export interface EventIndustryFilterOption {
  label: string;
  value: string;
}

export function buildEventFilterGroups(
  filters: EventFilterState,
  industryOptions: readonly EventIndustryFilterOption[] = [],
): EventFilterGroup[] {
  return [
    {
      key: 'time',
      label: '路由时间',
      options: markActive([
        { label: '3h', value: 'last-3h' },
        { label: '24h', value: 'last-24h' },
        { label: '3d', value: 'last-3d' },
        { label: '7d', value: 'last-7d' },
        { label: 'All', value: 'all-time' },
      ], filters.time),
    },
    {
      key: 'industry',
      label: '行业包',
      options: markActive(
        [
          { label: '全部行业', value: 'all-industries' },
          ...industryOptions,
        ],
        filters.industry,
      ),
    },
    {
      key: 'decision',
      label: '路由结果',
      options: markActive([
        { label: '默认重点', value: 'default' },
        { label: '进入行业分析', value: 'route' },
        { label: '需要复核', value: 'review' },
        { label: '已丢弃', value: 'discard' },
        { label: '全部含丢弃', value: 'all' },
      ], filters.decision || 'default'),
    },
  ];
}

export function buildEventSortOptions(sort: EventFilterState['sort']): EventFilterOption[] {
  return markActive([
    { label: '最新路由优先', value: 'routed_at_desc' },
    { label: '新闻发布时间优先', value: 'published_at_desc' },
  ], sort);
}

function markActive(
  options: Array<Omit<EventFilterOption, 'active'>>,
  activeValue: string,
): EventFilterOption[] {
  return options.map((option) => ({
    ...option,
    active: option.value === activeValue,
  }));
}
