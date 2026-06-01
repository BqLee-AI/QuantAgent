import type { RuntimeInspectListParams } from "../api";
import type { RuntimeDashboardFilters } from "../types/runtime-dashboard.types";

export const DEFAULT_RUNTIME_DASHBOARD_FILTERS: RuntimeDashboardFilters = {
  event_id: "",
  page: 1,
  page_size: 10,
  plugin_id: "",
  status: "",
  time_from: "",
  time_to: "",
  trace_id: "",
};

export function toRuntimeListParams(filters: RuntimeDashboardFilters): RuntimeInspectListParams {
  return {
    event_id: filters.event_id || null,
    page: filters.page,
    page_size: filters.page_size,
    plugin_id: filters.plugin_id || null,
    status: filters.status || null,
    time_from: filters.time_from || null,
    time_to: filters.time_to || null,
    trace_id: filters.trace_id || null,
  };
}

export function normalizeRuntimeSearch(
  value: Partial<RuntimeDashboardFilters> = {},
): RuntimeDashboardFilters {
  const page = Number(value.page);
  const pageSize = Number(value.page_size);

  return {
    event_id: value.event_id?.trim() ?? DEFAULT_RUNTIME_DASHBOARD_FILTERS.event_id,
    page:
      Number.isFinite(page) && page > 0 ? Math.floor(page) : DEFAULT_RUNTIME_DASHBOARD_FILTERS.page,
    page_size:
      Number.isFinite(pageSize) && pageSize > 0
        ? Math.min(Math.floor(pageSize), 100)
        : DEFAULT_RUNTIME_DASHBOARD_FILTERS.page_size,
    plugin_id: value.plugin_id?.trim() ?? DEFAULT_RUNTIME_DASHBOARD_FILTERS.plugin_id,
    status: value.status?.trim() ?? DEFAULT_RUNTIME_DASHBOARD_FILTERS.status,
    time_from: value.time_from?.trim() ?? DEFAULT_RUNTIME_DASHBOARD_FILTERS.time_from,
    time_to: value.time_to?.trim() ?? DEFAULT_RUNTIME_DASHBOARD_FILTERS.time_to,
    trace_id: value.trace_id?.trim() ?? DEFAULT_RUNTIME_DASHBOARD_FILTERS.trace_id,
  };
}

export function omitDefaultRuntimeSearch(
  filters: RuntimeDashboardFilters,
): Partial<RuntimeDashboardFilters> {
  const result: Partial<RuntimeDashboardFilters> = {};

  for (const key of Object.keys(DEFAULT_RUNTIME_DASHBOARD_FILTERS) as Array<
    keyof RuntimeDashboardFilters
  >) {
    if (filters[key] !== DEFAULT_RUNTIME_DASHBOARD_FILTERS[key]) {
      result[key] = filters[key] as never;
    }
  }

  return result;
}
