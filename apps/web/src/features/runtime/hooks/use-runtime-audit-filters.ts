import type {
  RuntimeAuditDecision,
  RuntimeAuditFilters,
  RuntimeAuditQueryParams,
  RuntimeAuditStatus,
} from '../types';

export const defaultRuntimeAuditFilters: RuntimeAuditFilters = {
  decision: 'all',
  event_id: '',
  industry: '',
  status: 'all',
  time_from: '',
  time_to: '',
  trace_id: '',
};

export function toRuntimeAuditFilters(
  value: Partial<RuntimeAuditFilters> = {},
): RuntimeAuditFilters {
  const textFilters = {
    event_id: value.event_id ?? defaultRuntimeAuditFilters.event_id,
    industry: value.industry ?? defaultRuntimeAuditFilters.industry,
    time_from: value.time_from ?? defaultRuntimeAuditFilters.time_from,
    time_to: value.time_to ?? defaultRuntimeAuditFilters.time_to,
    trace_id: value.trace_id ?? defaultRuntimeAuditFilters.trace_id,
  };

  return {
    ...defaultRuntimeAuditFilters,
    ...textFilters,
    decision: isRuntimeAuditDecision(value.decision) ? value.decision : 'all',
    status: isRuntimeAuditStatus(value.status) ? value.status : 'all',
  };
}

export function toRuntimeAuditSearch(
  value: Record<string, unknown>,
): Partial<RuntimeAuditFilters> {
  return {
    decision: isRuntimeAuditDecision(value.decision) ? value.decision : undefined,
    event_id: readSearchString(value.event_id),
    industry: readSearchString(value.industry),
    status: isRuntimeAuditStatus(value.status) ? value.status : undefined,
    time_from: readSearchString(value.time_from),
    time_to: readSearchString(value.time_to),
    trace_id: readSearchString(value.trace_id),
  };
}

export function toRuntimeAuditQueryParams(
  filters: RuntimeAuditFilters,
): RuntimeAuditQueryParams {
  return {
    decision: filters.decision === 'all' ? undefined : filters.decision,
    event_id: filters.event_id.trim() || undefined,
    industry: filters.industry.trim() || undefined,
    status: filters.status === 'all' ? undefined : filters.status,
    time_from: filters.time_from.trim() || undefined,
    time_to: filters.time_to.trim() || undefined,
    trace_id: filters.trace_id.trim() || undefined,
  };
}

export function isRuntimeAuditDecision(value: unknown): value is RuntimeAuditDecision | 'all' {
  return value === 'all' || value === 'discard' || value === 'review' || value === 'route';
}

export function isRuntimeAuditStatus(value: unknown): value is RuntimeAuditStatus | 'all' {
  return value === 'all' ||
    value === 'error' ||
    value === 'pending' ||
    value === 'success' ||
    value === 'unavailable' ||
    value === 'warning';
}

function readSearchString(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined;
}
