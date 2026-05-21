import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";

import { createApiClient, type ApiClient, ApiError } from "@/shared/api";
import { useRuntimeConfig } from "@/shared/config";

import { fetchCurrentActor, loginWithPassword, logoutSession } from "./api";
import type { AuthenticatedActor, AuthState, ForbiddenDetails } from "./types";

interface AuthContextValue extends AuthState {
  apiClient: ApiClient;
  bootstrap(): Promise<void>;
  login(password: string): Promise<void>;
  logout(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const DEVELOPMENT_ACTOR_ID = "local_dev";

function isDevelopmentActor(actor: AuthenticatedActor | null): boolean {
  return actor?.actor_id === DEVELOPMENT_ACTOR_ID;
}

function createUnauthenticatedState(isAuthDisabled: boolean): AuthState {
  return {
    actor: null,
    capabilities: new Set<string>(),
    csrfToken: null,
    forbidden: null,
    isAuthDisabled,
    lastForbiddenMessage: null,
    status: "unauthenticated",
  };
}

function createAuthenticatedState(
  actor: AuthenticatedActor,
  isAuthDisabled: boolean,
): AuthState {
  return {
    actor,
    capabilities: new Set(actor.capabilities),
    csrfToken: actor.csrf_token,
    forbidden: null,
    isAuthDisabled: isAuthDisabled && isDevelopmentActor(actor),
    lastForbiddenMessage: null,
    status: "authenticated",
  };
}

function isForbidden(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403;
}

function toForbiddenDetails(error: ApiError, fallbackMessage?: string): ForbiddenDetails {
  return {
    message: fallbackMessage ?? error.msg ?? "当前账号没有执行该操作的权限。",
    requestId: error.requestId ?? null,
    traceId: error.traceId ?? null,
  };
}

export function AuthProvider({ children }: PropsWithChildren) {
  const config = useRuntimeConfig();
  const [state, setState] = useState<AuthState>(() => ({
    ...createUnauthenticatedState(false),
    status: "bootstrapping",
  }));
  const csrfTokenRef = useRef<string | null>(null);

  const handleUnauthorized = useCallback(() => {
    csrfTokenRef.current = null;
    setState(createUnauthenticatedState(!config.authEnabled));
  }, [config.authEnabled]);

  const apiClient = useMemo(
    () =>
      createApiClient({
        baseURL: config.apiBaseUrl || undefined,
        getCsrfToken: () => csrfTokenRef.current,
        onError: (error) => {
          if (isForbidden(error)) {
            setState((current) => ({
              ...current,
              forbidden: toForbiddenDetails(error),
              lastForbiddenMessage: error.msg,
            }));
          }
        },
        onUnauthorized: handleUnauthorized,
        withCredentials: true,
      }),
    [config.apiBaseUrl, handleUnauthorized],
  );

  const setAuthenticatedActor = useCallback(
    (actor: AuthenticatedActor) => {
      csrfTokenRef.current = actor.csrf_token;
      setState(createAuthenticatedState(actor, !config.authEnabled));
    },
    [config.authEnabled],
  );

  const bootstrap = useCallback(async () => {
    setState((current) => ({ ...current, status: "bootstrapping" }));

    try {
      const actor = await fetchCurrentActor(apiClient);
      setAuthenticatedActor(actor);
    } catch (error) {
      if (isForbidden(error)) {
        const forbiddenError = error as ApiError
        setState((current) => ({
          ...current,
          forbidden: toForbiddenDetails(forbiddenError),
          lastForbiddenMessage: forbiddenError.msg,
          status: "authenticated",
        }));
        return
      }

      handleUnauthorized();
    }
  }, [apiClient, handleUnauthorized, setAuthenticatedActor]);

  const login = useCallback(
    async (password: string) => {
      const actor = await loginWithPassword(apiClient, { password });
      setAuthenticatedActor(actor);
    },
    [apiClient, setAuthenticatedActor],
  );

  const logout = useCallback(async () => {
    if (state.status !== "authenticated") {
      handleUnauthorized();
      return;
    }

    try {
      await logoutSession(apiClient);
    } finally {
      handleUnauthorized();
    }
  }, [apiClient, handleUnauthorized, state.status]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      apiClient,
      bootstrap,
      login,
      logout,
    }),
    [apiClient, bootstrap, login, logout, state],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);

  if (!value) {
    throw new Error("useAuth must be used within AuthProvider.");
  }

  return value;
}
