import type {
  RuntimeAuditFilters,
  RuntimeAuditNewsStage,
  RuntimeAuditNewsStatus,
  RuntimeAuditQueryParams,
} from '../types';

export const defaultRuntimeAuditFilters: RuntimeAuditFilters = {
  binding_id: '',
  current_stage: 'all',
  keyword: '',
  request_id: '',
  source_plugin_id: '',
  status: 'all',
  time_from: '',
  time_to: '',
  trace_id: '',
};

export function toRuntimeAuditFilters(
  value: Partial<RuntimeAuditFilters> = {},
): RuntimeAuditFilters {
  return {
    binding_id: value.binding_id ?? defaultRuntimeAuditFilters.binding_id,
    current_stage: isRuntimeAuditStage(value.current_stage) ? value.current_stage : 'all',
    keyword: value.keyword ?? defaultRuntimeAuditFilters.keyword,
    request_id: value.request_id ?? defaultRuntimeAuditFilters.request_id,
    source_plugin_id: value.source_plugin_id ?? defaultRuntimeAuditFilters.source_plugin_id,
    status: isRuntimeAuditNewsStatus(value.status) ? value.status : 'all',
    time_from: value.time_from ?? defaultRuntimeAuditFilters.time_from,
    time_to: value.time_to ?? defaultRuntimeAuditFilters.time_to,
    trace_id: value.trace_id ?? defaultRuntimeAuditFilters.trace_id,
  };
}

export function toRuntimeAuditSearch(
  value: Record<string, unknown>,
): Partial<RuntimeAuditFilters> {
  return {
    binding_id: readSearchString(value.binding_id),
    current_stage: isRuntimeAuditStage(value.current_stage) ? value.current_stage : undefined,
    keyword: readSearchString(value.keyword),
    request_id: readSearchString(value.request_id),
    source_plugin_id: readSearchString(value.source_plugin_id),
    status: isRuntimeAuditNewsStatus(value.status) ? value.status : undefined,
    time_from: readSearchString(value.time_from),
    time_to: readSearchString(value.time_to),
    trace_id: readSearchString(value.trace_id),
  };
}

export function toRuntimeAuditQueryParams(
  filters: RuntimeAuditFilters,
): RuntimeAuditQueryParams {
  return {
    binding_id: cleanText(filters.binding_id),
    current_stage: filters.current_stage === 'all' ? undefined : filters.current_stage,
    keyword: cleanText(filters.keyword),
    request_id: cleanText(filters.request_id),
    source_plugin_id: cleanText(filters.source_plugin_id),
    status: filters.status === 'all' ? undefined : filters.status,
    time_from: cleanText(filters.time_from),
    time_to: cleanText(filters.time_to),
    trace_id: cleanText(filters.trace_id),
  };
}

export function isRuntimeAuditNewsStatus(value: unknown): value is RuntimeAuditNewsStatus | 'all' {
  return value === 'all' ||
    value === 'captured' ||
    value === 'linked' ||
    value === 'pending' ||
    value === 'routed' ||
    value === 'unavailable';
}

export function isRuntimeAuditStage(value: unknown): value is RuntimeAuditNewsStage | 'all' {
  return value === 'all' ||
    value === 'captured' ||
    value === 'persisted' ||
    value === 'scheduler_linked' ||
    value === 'ai_intake_unavailable' ||
    value === 'ai_intake_routed' ||
    value === 'route_decided' ||
    value === 'route_unavailable';
}

function readSearchString(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined;
}

function cleanText(value: string): string | undefined {
  return value.trim() || undefined;
}
