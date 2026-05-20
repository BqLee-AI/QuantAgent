import { describe, expect, it } from "vitest";

import {
  isMockHttpResponse,
  isMockNetworkFailure,
  mockApiError,
  mockApiSuccess,
  mockHttpError,
  mockNetworkError,
  mockRecoverSequence,
  mockUnauthorized,
} from "../../../e2e/mocks/mockEnvelope";

describe("mockEnvelope helpers", () => {
  it("creates success envelopes without Playwright dependencies", () => {
    expect(
      mockApiSuccess({ ok: true }, {
        requestId: "req-success",
        traceId: "trace-success",
      }),
    ).toEqual({
      code: 0,
      data: { ok: true },
      msg: "ok",
      request_id: "req-success",
      trace_id: "trace-success",
    });
  });

  it("creates business error envelopes with consistent defaults", () => {
    expect(
      mockApiError({
        code: 40_001,
        msg: "参数错误",
      }),
    ).toEqual({
      code: 40_001,
      data: null,
      msg: "参数错误",
    });
  });

  it("distinguishes http errors from network failures", () => {
    const httpError = mockHttpError({
      status: 503,
      code: 50_300,
      msg: "temporary outage",
      requestId: "req-http",
    });
    const networkFailure = mockNetworkError({
      errorCode: "connectionrefused",
      reason: "connection dropped",
    });

    expect(isMockHttpResponse(httpError)).toBe(true);
    expect(httpError).toEqual({
      kind: "http",
      status: 503,
      headers: undefined,
      body: {
        code: 50_300,
        data: null,
        msg: "temporary outage",
        request_id: "req-http",
      },
    });

    expect(isMockNetworkFailure(networkFailure)).toBe(true);
    expect(networkFailure).toEqual({
      kind: "network",
      errorCode: "connectionrefused",
      reason: "connection dropped",
    });
  });

  it("creates unauthorized helpers and recover scenario placeholders", () => {
    const unauthorized = mockUnauthorized({
      requestId: "req-401",
    });
    const scenario = mockRecoverSequence({
      concurrentRequests: 3,
    });

    expect(unauthorized.status).toBe(401);
    expect(unauthorized.body).toEqual({
      code: 401,
      data: null,
      msg: "unauthorized",
      request_id: "req-401",
    });

    expect(scenario).toMatchObject({
      kind: "recover",
      mode: "concurrent",
      concurrentRequests: 3,
      initialUnauthorized: {
        status: 401,
      },
    });
  });
});
