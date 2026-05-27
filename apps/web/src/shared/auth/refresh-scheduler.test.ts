import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearRefreshState,
  REFRESH_RETRY_DELAY_MS,
  scheduleRefreshRetry,
  scheduleRefreshTimer,
  type RefreshTimerRefs,
} from "./refresh-scheduler";

function createRefs(): RefreshTimerRefs {
  return {
    nextRefreshAtMsRef: { current: null },
    timerRef: { current: null },
  };
}

describe("refresh scheduler", () => {
  beforeEach(() => {
    vi.stubGlobal("window", {
      clearTimeout: globalThis.clearTimeout,
      setTimeout: globalThis.setTimeout,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("schedules refresh before expiration and clears timer state", () => {
    vi.useFakeTimers();
    vi.setSystemTime(1_699_999_000_000);
    const refresh = vi.fn(async () => undefined);
    const refs = createRefs();

    scheduleRefreshTimer(refs, 1_700_000_000, refresh);

    expect(refs.nextRefreshAtMsRef.current).toBe(1_699_999_940_000);

    clearRefreshState(refs);

    expect(refs.nextRefreshAtMsRef.current).toBeNull();
    expect(refs.timerRef.current).toBeNull();
  });

  it("schedules retry with the fixed retry delay", () => {
    vi.useFakeTimers();
    vi.setSystemTime(1_700_000_000_000);
    const refresh = vi.fn(async () => undefined);
    const refs = createRefs();

    scheduleRefreshRetry(refs, refresh);

    expect(refs.nextRefreshAtMsRef.current).toBe(
      1_700_000_000_000 + REFRESH_RETRY_DELAY_MS,
    );
  });
});
