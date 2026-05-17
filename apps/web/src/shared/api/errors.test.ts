import { AxiosError, AxiosHeaders } from "axios";
import { describe, expect, it } from "vitest";

import {
  ApiError,
  ErrorRegistry,
  NETWORK_ERROR_CODE,
  createApiErrorFromEnvelope,
  getErrorRegistryEntry,
  toApiError,
} from "@/shared/api";

describe("ApiError", () => {
  it("keeps envelope metadata on business errors", () => {
    const error = createApiErrorFromEnvelope({
      code: 50_001,
      data: null,
      msg: "风控校验失败",
      request_id: "req-1",
      trace_id: "trace-1",
    });

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe(50_001);
    expect(error.msg).toBe("风控校验失败");
    expect(error.requestId).toBe("req-1");
    expect(error.traceId).toBe("trace-1");
  });

  it("converts axios http errors into ApiError", () => {
    const error = new AxiosError(
      "Request failed with status code 500",
      "ERR_BAD_RESPONSE",
      undefined,
      undefined,
      {
        config: {
          headers: new AxiosHeaders(),
        },
        data: {
          code: 70_001,
          data: null,
          msg: "后台去重",
          request_id: "req-500",
          trace_id: "trace-500",
        },
        headers: new AxiosHeaders({
          "x-request-id": "req-header",
          "x-trace-id": "trace-header",
        }),
        status: 500,
        statusText: "Internal Server Error",
      },
    );

    const apiError = toApiError(error);

    expect(apiError).toBeInstanceOf(ApiError);
    expect(apiError.code).toBe(70_001);
    expect(apiError.status).toBe(500);
    expect(apiError.requestId).toBe("req-500");
    expect(apiError.traceId).toBe("trace-500");
  });

  it("marks response-less axios failures as network errors", () => {
    const apiError = toApiError(new AxiosError("Network Error", "ERR_NETWORK"));

    expect(apiError.code).toBe(NETWORK_ERROR_CODE);
    expect(apiError.msg).toBe("Network Error");
  });

  it("exposes registry-backed default behaviors", () => {
    expect(ErrorRegistry.get(401)?.behavior).toBe("redirect");
    expect(getErrorRegistryEntry(50_001)?.behavior).toBe("modal");
  });
});
