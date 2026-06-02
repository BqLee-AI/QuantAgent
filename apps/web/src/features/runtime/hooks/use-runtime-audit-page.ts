import { useEffect, useMemo, useState } from 'react';

import { useRuntimeAuditMessagesQuery } from '../queries';
import type { RuntimeAuditFilters } from '../types';
import {
  toRuntimeAuditFilters,
  toRuntimeAuditQueryParams,
} from './use-runtime-audit-filters';
import { useRuntimeAuditSelection } from './use-runtime-audit-selection';
import { isRuntimeAuditPermissionDenied } from '../utils/runtime-audit-error';

export function useRuntimeAuditPage(search: Partial<RuntimeAuditFilters> = {}) {
  const {
    decision,
    event_id: eventId,
    industry,
    status,
    time_from: timeFrom,
    time_to: timeTo,
    trace_id: traceId,
  } = search;
  const [filters, setFilters] = useState<RuntimeAuditFilters>(() => toRuntimeAuditFilters(search));
  const normalizedSearchFilters = useMemo(
    () => toRuntimeAuditFilters({
      decision,
      event_id: eventId,
      industry,
      status,
      time_from: timeFrom,
      time_to: timeTo,
      trace_id: traceId,
    }),
    [decision, eventId, industry, status, timeFrom, timeTo, traceId],
  );

  useEffect(() => {
    // 中文注释：URL search 是深链入口，浏览器前进/后退后要回写页面筛选，避免显示和查询脱节。
    setFilters(normalizedSearchFilters);
  }, [normalizedSearchFilters]);

  const queryParams = useMemo(() => toRuntimeAuditQueryParams(filters), [filters]);
  const auditQuery = useRuntimeAuditMessagesQuery(queryParams);
  const groups = auditQuery.data?.groups ?? [];
  const messages = auditQuery.data?.messages ?? [];
  const selection = useRuntimeAuditSelection(groups, messages);

  function updateFilter<TKey extends keyof RuntimeAuditFilters>(
    key: TKey,
    value: RuntimeAuditFilters[TKey],
  ) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function resetFilters() {
    setFilters(toRuntimeAuditFilters());
  }

  return {
    auditQuery,
    filters,
    groups,
    health: auditQuery.data?.health ?? null,
    isPermissionDenied: isRuntimeAuditPermissionDenied(auditQuery.error),
    isFixtureMode: auditQuery.data?.fixture_mode ?? false,
    messages,
    queryParams,
    resetFilters,
    selection,
    updateFilter,
  };
}
