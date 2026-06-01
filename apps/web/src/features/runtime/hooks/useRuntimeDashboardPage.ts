import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";

import {
  useAgentRunsQuery,
  useRuntimeErrorsQuery,
  useRuntimeHealthQuery,
  useSchedulerRunsQuery,
  useToolInvocationsQuery,
} from "../queries";
import type {
  RuntimeDashboardFilterDraft,
  RuntimeDashboardFilters,
  RuntimeDashboardViewModel,
} from "../types";
import {
  getListUnavailableMessage,
  normalizeRuntimeSearch,
  omitDefaultRuntimeSearch,
} from "../utils";

function toDraft(filters: RuntimeDashboardFilters): RuntimeDashboardFilterDraft {
  return {
    eventId: filters.event_id,
    pluginId: filters.plugin_id,
    status: filters.status,
    timeFrom: filters.time_from,
    timeTo: filters.time_to,
    traceId: filters.trace_id,
  };
}

function toFilters(draft: RuntimeDashboardFilterDraft): RuntimeDashboardFilters {
  return normalizeRuntimeSearch({
    event_id: draft.eventId,
    page: 1,
    page_size: 10,
    plugin_id: draft.pluginId,
    status: draft.status,
    time_from: draft.timeFrom,
    time_to: draft.timeTo,
    trace_id: draft.traceId,
  });
}

export function useRuntimeDashboardPage(
  search: Partial<RuntimeDashboardFilters>,
): RuntimeDashboardViewModel {
  const navigate = useNavigate();
  const filters = useMemo(() => normalizeRuntimeSearch(search), [search]);
  const [draft, setDraft] = useState<RuntimeDashboardFilterDraft>(() => toDraft(filters));

  const healthQuery = useRuntimeHealthQuery();
  const agentRunsQuery = useAgentRunsQuery(filters);
  const toolInvocationsQuery = useToolInvocationsQuery(filters);
  const schedulerRunsQuery = useSchedulerRunsQuery(filters);
  const runtimeErrorsQuery = useRuntimeErrorsQuery(filters);
  const allQueries = [
    healthQuery,
    agentRunsQuery,
    toolInvocationsQuery,
    schedulerRunsQuery,
    runtimeErrorsQuery,
  ];
  const partialUnavailableCount = [
    ...(healthQuery.data?.unavailable_resources.map((resource) => resource.message) ?? []),
    getListUnavailableMessage(agentRunsQuery.data),
    getListUnavailableMessage(toolInvocationsQuery.data),
    getListUnavailableMessage(schedulerRunsQuery.data),
    getListUnavailableMessage(runtimeErrorsQuery.data),
  ].filter(Boolean).length;

  function updateDraft(nextDraft: Partial<RuntimeDashboardFilterDraft>) {
    setDraft((current) => ({ ...current, ...nextDraft }));
  }

  function applyFilters() {
    void navigate({
      search: omitDefaultRuntimeSearch(toFilters(draft)),
      to: "/runtime",
    });
  }

  function resetFilters() {
    const nextFilters = normalizeRuntimeSearch();
    setDraft(toDraft(nextFilters));
    void navigate({ search: {}, to: "/runtime" });
  }

  function refreshAll() {
    // 中文注释：Runtime Dashboard V1 只读，刷新只能重新读取 REST 快照，不能触发 scheduler 控制动作。
    for (const query of allQueries) {
      void query.refetch();
    }
  }

  return {
    agentRunsQuery,
    applyFilters,
    draft,
    filters,
    healthQuery,
    isRefreshing: allQueries.some((query) => query.isFetching),
    partialUnavailableCount,
    refreshAll,
    resetFilters,
    runtimeErrorsQuery,
    schedulerRunsQuery,
    toolInvocationsQuery,
    updateDraft,
  };
}
