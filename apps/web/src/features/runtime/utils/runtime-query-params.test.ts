import { describe, expect, it } from "vitest";

import {
  DEFAULT_RUNTIME_DASHBOARD_FILTERS,
  normalizeRuntimeSearch,
  omitDefaultRuntimeSearch,
  toRuntimeListParams,
} from "./runtime-query-params";

describe("runtime query params", () => {
  it("normalizes invalid search params to safe defaults", () => {
    expect(normalizeRuntimeSearch({ page: -1, page_size: 999 })).toEqual({
      ...DEFAULT_RUNTIME_DASHBOARD_FILTERS,
      page_size: 100,
    });
  });

  it("omits default search params before navigation", () => {
    expect(omitDefaultRuntimeSearch(DEFAULT_RUNTIME_DASHBOARD_FILTERS)).toEqual({});
  });

  it("maps empty filter strings to null API params", () => {
    expect(
      toRuntimeListParams({ ...DEFAULT_RUNTIME_DASHBOARD_FILTERS, trace_id: "trace-1" }),
    ).toEqual({
      event_id: null,
      page: 1,
      page_size: 10,
      plugin_id: null,
      status: null,
      time_from: null,
      time_to: null,
      trace_id: "trace-1",
    });
  });
});
