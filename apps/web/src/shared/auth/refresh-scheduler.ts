import { getSessionRefreshDelayMs } from "./refresh-timing";

export const REFRESH_RETRY_DELAY_MS = 5_000;

export interface RefreshTimerRefs {
  nextRefreshAtMsRef: { current: null | number };
  timerRef: { current: null | number };
}

export function clearRefreshState(refs: RefreshTimerRefs) {
  if (refs.timerRef.current !== null) {
    window.clearTimeout(refs.timerRef.current);
    refs.timerRef.current = null;
  }

  refs.nextRefreshAtMsRef.current = null;
}

export function scheduleRefreshTimer(
  refs: RefreshTimerRefs,
  expiresAt: number,
  refresh: () => Promise<void>,
) {
  const delayMs = getSessionRefreshDelayMs(expiresAt);
  clearRefreshState(refs);
  refs.nextRefreshAtMsRef.current = Date.now() + delayMs;
  refs.timerRef.current = window.setTimeout(() => {
    refs.nextRefreshAtMsRef.current = null;
    void refresh();
  }, delayMs);
}

export function scheduleRefreshRetry(
  refs: RefreshTimerRefs,
  refresh: () => Promise<void>,
) {
  clearRefreshState(refs);
  refs.nextRefreshAtMsRef.current = Date.now() + REFRESH_RETRY_DELAY_MS;
  refs.timerRef.current = window.setTimeout(() => {
    refs.nextRefreshAtMsRef.current = null;
    void refresh();
  }, REFRESH_RETRY_DELAY_MS);
}
