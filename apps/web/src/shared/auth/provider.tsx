import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";

import {
  AppRuntimeProvider,
} from "@/app/runtime/runtime.provider";
import { useApis } from "@/app/runtime/use-app-runtime";
import type { AuthRuntimeBridge } from "@/app/runtime/runtime.types";
import { useRuntimeConfig } from "@/shared/config";

import type { AuthApi } from "./api";
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

interface AuthProviderBridgeProps extends PropsWithChildren {
  authEnabled: boolean;
  nextRefreshAtMsRef: { current: null | number };
  onBootstrap(authApi: AuthApi): Promise<void>;
  onRefresh(authApi: AuthApi): Promise<void>;
  refreshRefs: Parameters<typeof clearRefreshState>[0];
  stateStatus: AuthState["status"];
  valueFactory(authApi: AuthApi): AuthContextValue;
}

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

function AuthProviderRuntimeBridge({
  authEnabled,
  children,
  nextRefreshAtMsRef,
  onBootstrap,
  onRefresh,
  refreshRefs,
  stateStatus,
  valueFactory,
}: AuthProviderBridgeProps) {
  const { auth } = useApis();

  useEffect(() => {
    void onBootstrap(auth);
  }, [auth, onBootstrap]);

  useEffect(() => () => clearRefreshState(refreshRefs), [refreshRefs]);

  useEffect(() => {
    if (!authEnabled || stateStatus !== "authenticated") {
      return;
    }

    const handleWindowFocus = () => {
      if (
        nextRefreshAtMsRef.current !== null &&
        Date.now() < nextRefreshAtMsRef.current
      ) {
        return;
      }

      void onRefresh(auth);
    };

    window.addEventListener("focus", handleWindowFocus);
    return () => {
      window.removeEventListener("focus", handleWindowFocus);
    };
  }, [auth, authEnabled, nextRefreshAtMsRef, onRefresh, stateStatus]);

  const value = useMemo<AuthContextValue>(() => valueFactory(auth), [auth, valueFactory]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
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

  const runtimeAuthBridge = useMemo<AuthRuntimeBridge>(
    () => ({
      getCsrfToken: () => csrfTokenRef.current,
      handleApiError: (error) => {
        if (error.status === 403) {
          setState((current) => ({
            ...current,
            forbidden: toForbiddenDetails(error),
            lastForbiddenMessage: error.msg,
          }));
        }
      },
      handleUnauthorized: resetToUnauthenticated,
    }),
    [resetToUnauthenticated],
  );

  const refreshAuthenticatedSession = useCallback(
    async (authApi: AuthApi) => {
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
        scheduleRefreshRetry(refreshRefs, () => refreshAuthenticatedSession(authApi));
        return;
      }

      if (result.kind === "unauthenticated") {
        clearSessionSideEffects(csrfTokenRef, refreshRefs);
        setState(result.state);
        return;
      }

      setState(nextState ?? result.state);

      if (result.kind === "refresh-forbidden") {
        scheduleRefreshRetry(refreshRefs, () => refreshAuthenticatedSession(authApi));
        return;
      }

      scheduleRefreshTimer(refreshRefs, result.actor.expires_at, () =>
        refreshAuthenticatedSession(authApi),
      );
    },
    [config.authEnabled, refreshRefs],
  );

  const bootstrap = useCallback(
    async (authApi: AuthApi) => {
      setState((current) => ({ ...current, status: "bootstrapping" }));

      const result = await bootstrapSession({
        authApi,
        isAuthDisabled: !config.authEnabled,
      });

      setState(applyBootstrapResult(result, csrfTokenRef));

      if (result.kind === "authenticated") {
        // 中文注释：`/me` 只有 actor 快照，首次 refresh 才能拿到刷新调度所需的过期时间。
        await refreshAuthenticatedSession(authApi);
        return;
      }

      if (result.kind === "unauthenticated") {
        clearSessionSideEffects(csrfTokenRef, refreshRefs);
      }
    },
    [config.authEnabled, refreshAuthenticatedSession, refreshRefs],
  );

  const login = useCallback(
    async (password: string, authApi: AuthApi) => {
      const result = await loginSession(
        { password },
        {
          authApi,
          isAuthDisabled: !config.authEnabled,
        },
      );

      syncCsrfToken(csrfTokenRef, result.state);
      setState(result.state);
      // 中文注释：登录返回没有 exp/max_exp，需主动 refresh 才能建立前端续期调度。
      await refreshAuthenticatedSession(authApi);
    },
    [config.authEnabled, refreshAuthenticatedSession],
  );

  const logout = useCallback(
    async (authApi: AuthApi) => {
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
    },
    [config.authEnabled, refreshRefs, state.status],
  );

  const valueFactory = useCallback(
    (authApi: AuthApi): AuthContextValue => ({
      ...state,
      bootstrap: () => bootstrap(authApi),
      login: (password: string) => login(password, authApi),
      logout: () => logout(authApi),
    }),
    [bootstrap, login, logout, state],
  );

  return (
    <AppRuntimeProvider auth={runtimeAuthBridge} config={config}>
      <AuthProviderRuntimeBridge
        authEnabled={config.authEnabled}
        nextRefreshAtMsRef={nextRefreshAtMsRef}
        onBootstrap={bootstrap}
        onRefresh={refreshAuthenticatedSession}
        refreshRefs={refreshRefs}
        stateStatus={state.status}
        valueFactory={valueFactory}
      >
        {children}
      </AuthProviderRuntimeBridge>
    </AppRuntimeProvider>
  );
}
