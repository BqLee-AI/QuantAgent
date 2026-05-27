import type { InternalAxiosRequestConfig } from "axios";
import { describe, expect, it } from "vitest";

import {
  ApiError,
  isApiResponse,
  normalizeResponse,
  type ApiResponse,
} from "@/shared/api";

function response<T>(data: T) {
  return {
    config: {} as InternalAxiosRequestConfig,
    data,
    headers: {},
    status: 200,
    statusText: "OK",
  };
}

describe("isApiResponse", () => {
  it("recognizes API envelopes", () => {
    expect(isApiResponse({ code: 0, data: null, msg: "ok" })).toBe(true);
    expect(isApiResponse({ data: null, msg: "ok" })).toBe(false);
  });
});

describe("normalizeResponse", () => {
  it("unwraps successful envelopes", () => {
    expect(
      normalizeResponse(
        response<ApiResponse<{ id: number }>>({
          code: 0,
          data: { id: 1 },
          msg: "ok",
        }),
        {},
      ),
    ).toEqual({ id: 1 });
  });

  it("returns envelopes when requested", () => {
    const envelope = { code: 0, data: { id: 1 }, msg: "ok" };

    expect(
      normalizeResponse(response<ApiResponse<{ id: number }>>(envelope), {
        _returnEnvelope: true,
      }),
    ).toEqual(envelope);
  });

  it("turns malformed or non-zero envelopes into ApiError", () => {
    expect(() =>
      normalizeResponse(
        response({ ok: true }) as unknown as Parameters<
          typeof normalizeResponse
        >[0],
        {},
      ),
    ).toThrow(ApiError);
    expect(() =>
      normalizeResponse(
        response<ApiResponse<null>>({
          code: 40_001,
          data: null,
          msg: "参数错误",
          request_id: "req-1",
        }),
        {},
      ),
    ).toThrow(ApiError);
  });
});
