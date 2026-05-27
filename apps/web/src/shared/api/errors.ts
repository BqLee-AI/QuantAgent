import axios from "axios";

import type { ApiResponse } from "./types";

export type ErrorBehavior = "modal" | "redirect" | "silent" | "toast";

export interface ErrorRegistryEntry {
  behavior: ErrorBehavior;
  message?: string;
}

export interface ApiErrorOptions {
  code: number;
  msg: string;
  requestId?: string;
  traceId?: string;
  status?: number;
  cause?: unknown;
}

export const NETWORK_ERROR_CODE = -1;
export const UNKNOWN_ERROR_CODE = -2;

export class ApiError extends Error {
  readonly code: number;
  readonly msg: string;
  readonly requestId?: string;
  readonly traceId?: string;
  readonly status?: number;

  constructor(options: ApiErrorOptions) {
    super(options.msg, { cause: options.cause });
    this.name = "ApiError";
    this.code = options.code;
    this.msg = options.msg;
    this.requestId = options.requestId;
    this.traceId = options.traceId;
    this.status = options.status;
  }
}

export const ErrorRegistry = new Map<number, ErrorRegistryEntry>([
  [401, { behavior: "redirect", message: "登录状态已失效，请重新认证。" }],
  [403, { behavior: "modal", message: "当前账号没有执行该操作的权限。" }],
  [429, { behavior: "toast", message: "请求过于频繁，请稍后重试。" }],
  [50_001, { behavior: "modal", message: "风控校验未通过，请联系管理员。" }],
  [70_001, { behavior: "silent", message: "请求已被后台去重处理。" }],
]);

// TODO: Align business error code coverage with backend-owned code definitions.

function readHeader(
  headers: unknown,
  candidates: readonly string[],
): string | undefined {
  if (!headers || typeof headers !== "object") {
    return undefined;
  }

  const normalized = headers as Record<string, unknown>;

  for (const candidate of candidates) {
    const exact = normalized[candidate];

    if (typeof exact === "string" && exact.length > 0) {
      return exact;
    }

    const lower = normalized[candidate.toLowerCase()];

    if (typeof lower === "string" && lower.length > 0) {
      return lower;
    }
  }

  return undefined;
}

function isApiResponse<T>(value: unknown): value is ApiResponse<T> {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ApiResponse<T>>;

  return (
    typeof candidate.code === "number" &&
    typeof candidate.msg === "string" &&
    "data" in candidate
  );
}

export function createApiErrorFromEnvelope(
  envelope: ApiResponse<unknown>,
  status?: number,
  cause?: unknown,
): ApiError {
  return new ApiError({
    code: envelope.code,
    msg: envelope.msg,
    requestId: envelope.request_id,
    traceId: envelope.trace_id,
    status,
    cause,
  });
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (axios.isAxiosError(error)) {
    const payload = error.response?.data;
    const status = error.response?.status;
    const requestId = readHeader(error.response?.headers, [
      "request_id",
      "x-request-id",
    ]);
    const traceId = readHeader(error.response?.headers, [
      "trace_id",
      "x-trace-id",
    ]);

    if (isApiResponse(payload)) {
      return new ApiError({
        code: payload.code,
        msg: payload.msg,
        requestId: payload.request_id ?? requestId,
        traceId: payload.trace_id ?? traceId,
        status,
        cause: error,
      });
    }

    if (status) {
      return new ApiError({
        code: status,
        msg:
          (typeof payload === "object" &&
            payload &&
            "message" in payload &&
            typeof payload.message === "string" &&
            payload.message) ||
          error.message ||
          "HTTP request failed.",
        requestId,
        traceId,
        status,
        cause: error,
      });
    }

    return new ApiError({
      code: NETWORK_ERROR_CODE,
      msg: error.message || "Network request failed.",
      cause: error,
    });
  }

  if (error instanceof Error) {
    return new ApiError({
      code: UNKNOWN_ERROR_CODE,
      msg: error.message,
      cause: error,
    });
  }

  return new ApiError({
    code: UNKNOWN_ERROR_CODE,
    msg: "Unexpected API error.",
    cause: error,
  });
}

export function getErrorRegistryEntry(code: number): ErrorRegistryEntry | undefined {
  return ErrorRegistry.get(code);
}
