import { describe, expect, it } from "vitest";

import { ApiError } from "@/shared/api";

import {
  formatDuration,
  formatErrorSummary,
  formatObjectSummary,
  formatRuntimeApiError,
  isPermissionDeniedError,
} from "./runtime-format";

describe("runtime format helpers", () => {
  it("keeps request id visible for API errors", () => {
    const error = new ApiError({
      code: 403,
      msg: "缺少 runtime.inspect",
      requestId: "req-1",
      status: 403,
    });

    expect(formatRuntimeApiError(error)).toBe("缺少 runtime.inspect（Request ID: req-1）");
    expect(isPermissionDeniedError(error)).toBe(true);
  });

  it("formats duration and structured summaries", () => {
    expect(formatDuration(850)).toBe("850 ms");
    expect(formatDuration(1500)).toBe("1.5 s");
    expect(formatObjectSummary({ total_tokens: 32, cost: "0.01" })).toBe(
      "total_tokens: 32 · cost: 0.01",
    );
    expect(
      formatErrorSummary({
        error_code: "TOOL_FAILED",
        error_message_summary: "工具失败",
        failure_stage: "invoke",
      }),
    ).toBe("TOOL_FAILED: 工具失败 · invoke");
  });
});
