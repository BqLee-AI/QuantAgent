import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";

import {
  createApiClient,
  createBaseApi,
  type ApiClient,
  type BaseApi,
} from "@/shared/api";
import { useRuntimeConfig } from "@/shared/config";

import { createAuthApi, type AuthApi } from "./api";
import { AuthContext } from "./context";
import { toForbiddenDetails } from "./forbidden";
import type { AuthContextValue, AuthState } from "./models";
import {
  clearRefreshState,
  REFRESH_RETRY_DELAY_MS,
  scheduleRefreshRetry,
  scheduleRefreshTimer,
} from "./refresh-scheduler";
import {
  bootstrapSession,
  loginSession,
  logoutSession,
  refreshSession,
  type BootstrapSessionResult,
  type RefreshSessionResult,
} from "./session-actions";
import {
  createBootstrappingState,
  createUnauthenticatedState,
} from "./state";

function syncCsrfToken(
  csrfTokenRef: { current: string | null },
  state: AuthState,
) {
  csrfTokenRef.current = state.csrfToken;
}

function clearSessionSideEffects(
  csrfTokenRef: { current: string | null },
  refreshRefs: Parameters<typeof clearRefreshState>[0],
) {
  clearRefreshState(refreshRefs);
  csrfTokenRef.current = null;
}

function applyBootstrapResult(
  result: BootstrapSessionResult,
  csrfTokenRef: { current: string | null },
): AuthState {
  syncCsrfToken(csrfTokenRef, result.state);
  return result.state;
}

function applyRefreshResult(
  result: RefreshSessionResult,
  csrfTokenRef: { current: string | null },
): AuthState | null {
  if (result.kind === "refresh-retry") {
    return null;
  }

  syncCsrfToken(csrfTokenRef, result.state);
  return result.state;
}

export function AuthProvider({ children }: PropsWithChildren) {
  const config = useRuntimeConfig();
  const [state, setState] = useState<AuthState>(createBootstrappingState);
  const csrfTokenRef = useRef<string | null>(null);
  const refreshTimerRef = useRef<null | number>(null);
  const nextRefreshAtMsRef = useRef<null | number>(null);
  const lastRefreshAttemptAtMsRef = useRef(0);
  const refreshRefs = useMemo(
    () => ({
      nextRefreshAtMsRef,
      timerRef: refreshTimerRef,
    }),
    [],
  );

  const resetToUnauthenticated = useCallback(() => {
    clearSessionSideEffects(csrfTokenRef, refreshRefs);
    setState(createUnauthenticatedState(!config.authEnabled));
  }, [config.authEnabled, refreshRefs]);

  const apiClient = useMemo<ApiClient>(
    () =>
      createApiClient({
        baseURL: config.apiBaseUrl || undefined,
        getCsrfToken: () => csrfTokenRef.current,
        onError: (error) => {
          if (error.status === 403) {
            setState((current) => ({
              ...current,
              forbidden: toForbiddenDetails(error),
              lastForbiddenMessage: error.msg,
            }));
          }
        },
        onUnauthorized: resetToUnauthenticated,
        withCredentials: true,
      }),
    [config.apiBaseUrl, resetToUnauthenticated],
  );
  const baseApi = useMemo<BaseApi>(() => createBaseApi(apiClient), [apiClient]);
  const authApi = useMemo<AuthApi>(() => createAuthApi(baseApi), [baseApi]);

  const refreshAuthenticatedSession = useCallback(async () => {
    if (!config.authEnabled || !csrfTokenRef.current) {
      clearRefreshState(refreshRefs);
      return;
    }

    const nowMs = Date.now();
    if (nowMs - lastRefreshAttemptAtMsRef.current < REFRESH_RETRY_DELAY_MS) {
      return;
    }

    lastRefreshAttemptAtMsRef.current = nowMs;

    const result = await refreshSession({
      authApi,
      isAuthDisabled: !config.authEnabled,
    });

    const nextState = applyRefreshResult(result, csrfTokenRef);

    if (result.kind === "refresh-retry") {
      scheduleRefreshRetry(refreshRefs, refreshAuthenticatedSession);
      return;
    }

    if (result.kind === "unauthenticated") {
      clearSessionSideEffects(csrfTokenRef, refreshRefs);
      setState(result.state);
      return;
    }

    setState(nextState ?? result.state);

    if (result.kind === "refresh-forbidden") {
      scheduleRefreshRetry(refreshRefs, refreshAuthenticatedSession);
      return;
    }

    scheduleRefreshTimer(
      refreshRefs,
      result.actor.expires_at,
      refreshAuthenticatedSession,
    );
  }, [authApi, config.authEnabled, refreshRefs]);

  const bootstrap = useCallback(async () => {
    setState((current) => ({ ...current, status: "bootstrapping" }));

    const result = await bootstrapSession({
      authApi,
      isAuthDisabled: !config.authEnabled,
    });

    setState(applyBootstrapResult(result, csrfTokenRef));

    if (result.kind === "authenticated") {
      // `/me` only returns the actor snapshot. Prime refresh once to learn idle expiration.
      await refreshAuthenticatedSession();
      return;
    }

    if (result.kind === "unauthenticated") {
      clearSessionSideEffects(csrfTokenRef, refreshRefs);
    }
  }, [authApi, config.authEnabled, refreshAuthenticatedSession, refreshRefs]);

  const login = useCallback(
    async (password: string) => {
      const result = await loginSession(
        { password },
        {
          authApi,
          isAuthDisabled: !config.authEnabled,
        },
      );

      syncCsrfToken(csrfTokenRef, result.state);
      setState(result.state);
      // Login response does not include exp/max_exp, so refresh seeds the first timer.
      await refreshAuthenticatedSession();
    },
    [authApi, config.authEnabled, refreshAuthenticatedSession],
  );

  const logout = useCallback(async () => {
    try {
      const result = await logoutSession(state.status === "authenticated", {
        authApi,
        isAuthDisabled: !config.authEnabled,
      });

      setState(result.state);
    } finally {
      clearSessionSideEffects(csrfTokenRef, refreshRefs);
      setState(createUnauthenticatedState(!config.authEnabled));
    }
  }, [authApi, config.authEnabled, refreshRefs, state.status]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  useEffect(() => () => clearRefreshState(refreshRefs), [refreshRefs]);

  useEffect(() => {
    if (!config.authEnabled || state.status !== "authenticated") {
      return;
    }

    const handleWindowFocus = () => {
      if (
        nextRefreshAtMsRef.current !== null &&
        Date.now() < nextRefreshAtMsRef.current
      ) {
        return;
      }

      void refreshAuthenticatedSession();
    };

    window.addEventListener("focus", handleWindowFocus);
    return () => {
      window.removeEventListener("focus", handleWindowFocus);
    };
  }, [config.authEnabled, refreshAuthenticatedSession, state.status]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      apiClient,
      baseApi,
      bootstrap,
      login,
      logout,
    }),
    [apiClient, baseApi, bootstrap, login, logout, state],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
