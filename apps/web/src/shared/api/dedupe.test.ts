import { describe, expect, it } from "vitest";

import { getDedupeKey } from "@/shared/api";

describe("getDedupeKey", () => {
  it("deduplicates read requests by default", () => {
    expect(
      getDedupeKey({
        baseURL: "/api/v1",
        method: "get",
        params: { page: 1 },
        url: "/events",
      }),
    ).toBe('get:/api/v1:/events:{"page":1}:data');
  });

  it("keeps envelope and data callers separate", () => {
    expect(
      getDedupeKey({
        _returnEnvelope: true,
        method: "get",
        url: "/events",
      }),
    ).toBe("get::/events::envelope");
  });

  it("does not deduplicate writes, aborted requests, or explicit opt-outs", () => {
    expect(getDedupeKey({ method: "post", url: "/events" })).toBeUndefined();
    expect(
      getDedupeKey({
        dedupeKey: false,
        method: "get",
        url: "/events",
      }),
    ).toBeUndefined();
    expect(
      getDedupeKey({
        method: "get",
        signal: new AbortController().signal,
        url: "/events",
      }),
    ).toBeUndefined();
  });
});
