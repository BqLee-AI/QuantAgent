import { describe, expect, it } from "vitest";

import { ApiError } from "@/shared/api";

import { isForbidden, toForbiddenDetails } from "./forbidden";

describe("forbidden helpers", () => {
  it("maps 403 ApiError to forbidden details", () => {
    const error = new ApiError({
      code: 403,
      msg: "forbidden",
      requestId: "req-1",
      status: 403,
      traceId: "trace-1",
    });

    expect(isForbidden(error)).toBe(true);
    expect(toForbiddenDetails(error)).toEqual({
      message: "forbidden",
      requestId: "req-1",
      traceId: "trace-1",
    });
  });

  it("does not treat non-403 ApiError as forbidden", () => {
    expect(
      isForbidden(
        new ApiError({
          code: 401,
          msg: "unauthorized",
          status: 401,
        }),
      ),
    ).toBe(false);
  });
});
