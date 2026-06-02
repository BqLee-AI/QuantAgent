import { ApiError } from '@/shared/api';

export function isRuntimeAuditPermissionDenied(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 403 || error.code === 403);
}

export function formatRuntimeAuditErrorMeta(error: unknown): string | null {
  if (!(error instanceof ApiError)) {
    return null;
  }

  const items = [
    error.requestId ? `request_id: ${error.requestId}` : null,
    error.traceId ? `trace_id: ${error.traceId}` : null,
  ].filter(Boolean);

  return items.length > 0 ? items.join(' / ') : null;
}
