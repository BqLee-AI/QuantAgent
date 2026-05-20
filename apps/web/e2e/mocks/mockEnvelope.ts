import type { ApiResponse } from "../../src/shared/api/types";

export type MockRouteAbortCode =
  | "aborted"
  | "accessdenied"
  | "addressunreachable"
  | "blockedbyclient"
  | "blockedbyresponse"
  | "connectionaborted"
  | "connectionclosed"
  | "connectionfailed"
  | "connectionrefused"
  | "connectionreset"
  | "internetdisconnected"
  | "namenotresolved"
  | "timedout"
  | "failed";

export interface MockEnvelopeOverrides {
  requestId?: string;
  traceId?: string;
}

export interface MockApiSuccessOptions extends MockEnvelopeOverrides {
  msg?: string;
}

export interface MockApiErrorOptions extends MockEnvelopeOverrides {
  code?: number;
  msg?: string;
}

export interface MockHttpErrorOptions<TBody = null> extends MockEnvelopeOverrides {
  body?: ApiResponse<TBody>;
  code?: number;
  data?: TBody | null;
  headers?: Record<string, string>;
  msg?: string;
  status?: number;
}

export interface MockNetworkErrorOptions {
  errorCode?: MockRouteAbortCode;
  reason?: string;
}

export interface MockUnauthorizedOptions extends MockEnvelopeOverrides {
  msg?: string;
}

export interface MockHttpResponse<TBody = unknown> {
  kind: "http";
  status: number;
  body: ApiResponse<TBody>;
  headers?: Record<string, string>;
}

export interface MockNetworkFailure {
  kind: "network";
  errorCode: MockRouteAbortCode;
  reason: string;
}

export interface MockRecoverScenario {
  kind: "recover";
  mode: "single" | "concurrent";
  concurrentRequests: number;
  initialUnauthorized: MockHttpResponse<null>;
  recoverResponse: MockHttpResponse | MockNetworkFailure | ApiResponse<unknown>;
  replayResponse?: MockHttpResponse | MockNetworkFailure | ApiResponse<unknown>;
}

function withEnvelopeMetadata<TData>(
  envelope: {
    code: number;
    data: TData | null;
    msg: string;
  },
  options: MockEnvelopeOverrides,
): ApiResponse<TData | null> {
  return {
    ...envelope,
    ...(options.requestId ? { request_id: options.requestId } : {}),
    ...(options.traceId ? { trace_id: options.traceId } : {}),
  };
}

export function mockApiSuccess<TData>(
  data: TData,
  options: MockApiSuccessOptions = {},
): ApiResponse<TData> {
  return withEnvelopeMetadata(
    {
      code: 0,
      data,
      msg: options.msg ?? "ok",
    },
    options,
  ) as ApiResponse<TData>;
}

export function mockApiError(
  options: MockApiErrorOptions = {},
): ApiResponse<null> {
  return withEnvelopeMetadata(
    {
      code: options.code ?? 40_000,
      data: null,
      msg: options.msg ?? "mocked business error",
    },
    options,
  ) as ApiResponse<null>;
}

export function mockHttpError<TBody = null>(
  options: MockHttpErrorOptions<TBody> = {},
): MockHttpResponse<TBody | null> {
  return {
    kind: "http",
    status: options.status ?? 500,
    headers: options.headers,
    body: options.body ??
      withEnvelopeMetadata(
        {
          code: options.code ?? options.status ?? 50_000,
          data: (options.data ?? null) as TBody | null,
          msg: options.msg ?? "mocked http error",
        },
        options,
      ),
  };
}

export function mockNetworkError(
  options: MockNetworkErrorOptions = {},
): MockNetworkFailure {
  return {
    kind: "network",
    errorCode: options.errorCode ?? "failed",
    reason: options.reason ?? "mocked network failure",
  };
}

export function mockUnauthorized(
  options: MockUnauthorizedOptions = {},
): MockHttpResponse<null> {
  return mockHttpError({
    status: 401,
    code: 401,
    msg: options.msg ?? "unauthorized",
    requestId: options.requestId,
    traceId: options.traceId,
  });
}

export function mockRecoverSequence(options: {
  concurrentRequests?: number;
  recoverResponse?: MockHttpResponse | MockNetworkFailure | ApiResponse<unknown>;
  replayResponse?: MockHttpResponse | MockNetworkFailure | ApiResponse<unknown>;
} = {}): MockRecoverScenario {
  return {
    kind: "recover",
    mode: options.concurrentRequests && options.concurrentRequests > 1 ? "concurrent" : "single",
    concurrentRequests: Math.max(1, options.concurrentRequests ?? 1),
    initialUnauthorized: mockUnauthorized(),
    recoverResponse:
      options.recoverResponse ?? mockApiSuccess({ recovered: true } as const),
    replayResponse:
      options.replayResponse ?? mockApiSuccess({ replayed: true } as const),
  };
}

export function isMockHttpResponse(
  value: unknown,
): value is MockHttpResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "kind" in value &&
    (value as { kind?: string }).kind === "http"
  );
}

export function isMockNetworkFailure(
  value: unknown,
): value is MockNetworkFailure {
  return (
    typeof value === "object" &&
    value !== null &&
    "kind" in value &&
    (value as { kind?: string }).kind === "network"
  );
}
