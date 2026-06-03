import { useEffect, useMemo, useState } from 'react';

import { useRuntimeAuditNewsQuery } from '../queries';
import type { RuntimeAuditFilters, RuntimeAuditHealthSummary } from '../types';
import { isRuntimeAuditPermissionDenied } from '../utils/runtime-audit-error';
import {
  toRuntimeAuditFilters,
  toRuntimeAuditQueryParams,
} from './use-runtime-audit-filters';
import { useRuntimeAuditSelection } from './use-runtime-audit-selection';

export function useRuntimeAuditPage(search: Partial<RuntimeAuditFilters> = {}) {
  const {
    binding_id: bindingId,
    current_stage: currentStage,
    keyword,
    request_id: requestId,
    source_plugin_id: sourcePluginId,
    status,
    time_from: timeFrom,
    time_to: timeTo,
    trace_id: traceId,
  } = search;
  const [filters, setFilters] = useState<RuntimeAuditFilters>(() => toRuntimeAuditFilters(search));
  const normalizedSearchFilters = useMemo(
    () => toRuntimeAuditFilters({
      binding_id: bindingId,
      current_stage: currentStage,
      keyword,
      request_id: requestId,
      source_plugin_id: sourcePluginId,
      status,
      time_from: timeFrom,
      time_to: timeTo,
      trace_id: traceId,
    }),
    [bindingId, currentStage, keyword, requestId, sourcePluginId, status, timeFrom, timeTo, traceId],
  );

  useEffect(() => {
    // 中文注释：URL search 是深链入口，浏览器前进/后退后要回写页面筛选，避免显示和查询脱节。
    setFilters(normalizedSearchFilters);
  }, [normalizedSearchFilters]);

  const queryParams = useMemo(() => toRuntimeAuditQueryParams(filters), [filters]);
  const auditQuery = useRuntimeAuditNewsQuery(queryParams);
  const items = useMemo(() => auditQuery.data?.items ?? [], [auditQuery.data?.items]);
  const selection = useRuntimeAuditSelection(items);
  const health = useMemo<RuntimeAuditHealthSummary | null>(() => {
    if (!auditQuery.data) return null;
    const unavailableCount = items.filter((item) => item.timeline.some((step) => step.status === 'unavailable')).length;
    return {
      generated_at: auditQuery.data.generated_at,
      label: 'RawEvent news read model',
      partial_unavailable_count: unavailableCount,
      status: unavailableCount > 0 ? 'degraded' : 'healthy',
      total_items: items.length,
    };
  }, [auditQuery.data, items]);

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
    health,
    isPermissionDenied: isRuntimeAuditPermissionDenied(auditQuery.error),
    items,
    queryParams,
    resetFilters,
    selection,
    updateFilter,
  };
}
