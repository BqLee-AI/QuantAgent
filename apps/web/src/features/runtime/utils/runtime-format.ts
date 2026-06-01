import { ApiError } from "@/shared/api";

import type { RuntimeErrorSummaryPayload, RuntimeListResponse } from "../api";

export function formatRuntimeApiError(error: unknown): string {
  if (error instanceof ApiError) {
    const requestId = error.requestId ? `（Request ID: ${error.requestId}）` : "";
    return `${error.msg}${requestId}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "运行态数据加载失败。";
}

export function isPermissionDeniedError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

export function formatDuration(durationMs: number | null | undefined): string {
  if (durationMs === null || durationMs === undefined) {
    return "-";
  }

  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }

  return `${(durationMs / 1000).toFixed(1)} s`;
}

export function formatErrorSummary(
  errorSummary: RuntimeErrorSummaryPayload | null | undefined,
): string {
  if (!errorSummary) {
    return "-";
  }

  const stage = errorSummary.failure_stage ? ` · ${errorSummary.failure_stage}` : "";
  return `${errorSummary.error_code}: ${errorSummary.error_message_summary}${stage}`;
}

export function formatObjectSummary(value: Record<string, unknown> | null | undefined): string {
  if (!value) {
    return "-";
  }

  const entries = Object.entries(value).filter(
    ([, entryValue]) => entryValue !== null && entryValue !== undefined,
  );
  if (entries.length === 0) {
    return "-";
  }

  return entries
    .slice(0, 3)
    .map(([key, entryValue]) => `${key}: ${String(entryValue)}`)
    .join(" · ");
}

export function getListUnavailableMessage<TItem>(
  data: RuntimeListResponse<TItem> | undefined,
): string | null {
  if (!data || data.meta.state !== "unavailable") {
    return null;
  }

  return data.meta.unavailable?.message ?? "该资源当前不可用。";
}
