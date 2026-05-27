import { ApiError } from "@/shared/api";

import type { ForbiddenDetails } from "./models";

export function isForbidden(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 403;
}

export function toForbiddenDetails(
  error: ApiError,
  fallbackMessage?: string,
): ForbiddenDetails {
  return {
    message: fallbackMessage ?? error.msg ?? "当前账号没有执行该操作的权限。",
    requestId: error.requestId ?? null,
    traceId: error.traceId ?? null,
  };
}
