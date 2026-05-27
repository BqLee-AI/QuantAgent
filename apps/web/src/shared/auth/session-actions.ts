import { ApiError } from "@/shared/api";

import type { AuthApiContract } from "./api";
import { isForbidden, toForbiddenDetails } from "./forbidden";
import type {
  AuthenticatedActor,
  AuthState,
  ForbiddenDetails,
  LoginPayload,
  LogoutResponse,
  RefreshedSession,
} from "./models";
import {
  createAuthenticatedState,
  createUnauthenticatedState,
} from "./state";

export type SessionActionKind =
  | "authenticated"
  | "forbidden"
  | "refreshed"
  | "refresh-forbidden"
  | "refresh-retry"
  | "unauthenticated";

export interface AuthenticatedSessionResult {
  actor: AuthenticatedActor;
  kind: "authenticated";
  state: AuthState;
}

export interface ForbiddenSessionResult {
  details: ForbiddenDetails;
  kind: "forbidden";
  message: string;
  state: AuthState;
}

export interface RefreshForbiddenSessionResult {
  actor: AuthenticatedActor;
  kind: "refresh-forbidden";
  state: AuthState;
}

export interface RefreshedSessionResult {
  actor: RefreshedSession;
  kind: "refreshed";
  state: AuthState;
}

export interface RefreshRetrySessionResult {
  kind: "refresh-retry";
}

export interface UnauthenticatedSessionResult {
  kind: "unauthenticated";
  state: AuthState;
}

export type BootstrapSessionResult =
  | AuthenticatedSessionResult
  | ForbiddenSessionResult
  | UnauthenticatedSessionResult;

export type LoginSessionResult = AuthenticatedSessionResult;

export interface LogoutSessionResult {
  logout?: LogoutResponse;
  state: AuthState;
}

export type RefreshSessionResult =
  | RefreshForbiddenSessionResult
  | RefreshedSessionResult
  | RefreshRetrySessionResult
  | UnauthenticatedSessionResult;

export interface SessionActionOptions {
  authApi: AuthApiContract;
  isAuthDisabled: boolean;
}

function toUnauthenticatedResult(
  isAuthDisabled: boolean,
): UnauthenticatedSessionResult {
  return {
    kind: "unauthenticated",
    state: createUnauthenticatedState(isAuthDisabled),
  };
}

function toAuthenticatedResult(
  actor: AuthenticatedActor,
  isAuthDisabled: boolean,
): AuthenticatedSessionResult {
  return {
    actor,
    kind: "authenticated",
    state: createAuthenticatedState(actor, isAuthDisabled),
  };
}

export async function bootstrapSession({
  authApi,
  isAuthDisabled,
}: SessionActionOptions): Promise<BootstrapSessionResult> {
  try {
    const actor = await authApi.fetchCurrentActor();

    return toAuthenticatedResult(actor, isAuthDisabled);
  } catch (error) {
    if (isForbidden(error)) {
      const details = toForbiddenDetails(error);

      return {
        details,
        kind: "forbidden",
        message: error.msg,
        state: {
          ...createUnauthenticatedState(isAuthDisabled),
          forbidden: details,
          lastForbiddenMessage: error.msg,
          status: "authenticated",
        },
      };
    }

    if (error instanceof ApiError && error.status === 401) {
      return toUnauthenticatedResult(isAuthDisabled);
    }

    return toUnauthenticatedResult(isAuthDisabled);
  }
}

export async function loginSession(
  payload: LoginPayload,
  { authApi, isAuthDisabled }: SessionActionOptions,
): Promise<LoginSessionResult> {
  const actor = await authApi.loginWithPassword(payload);

  return toAuthenticatedResult(actor, isAuthDisabled);
}

export async function logoutSession(
  shouldCallLogout: boolean,
  { authApi, isAuthDisabled }: SessionActionOptions,
): Promise<LogoutSessionResult> {
  let logout: LogoutResponse | undefined;

  if (shouldCallLogout) {
    logout = await authApi.logoutSession();
  }

  return {
    logout,
    state: createUnauthenticatedState(isAuthDisabled),
  };
}

export async function refreshSession({
  authApi,
  isAuthDisabled,
}: SessionActionOptions): Promise<RefreshSessionResult> {
  try {
    const refreshedSession = await authApi.refreshCurrentSession();

    return {
      actor: refreshedSession,
      kind: "refreshed",
      state: createAuthenticatedState(refreshedSession, isAuthDisabled),
    };
  } catch (error) {
    if (!(error instanceof ApiError)) {
      throw error;
    }

    if (error.status === 401) {
      return toUnauthenticatedResult(isAuthDisabled);
    }

    if (error.status === 403) {
      try {
        const actor = await authApi.fetchCurrentActor();

        return {
          actor,
          kind: "refresh-forbidden",
          state: createAuthenticatedState(actor, isAuthDisabled),
        };
      } catch (bootstrapError) {
        if (!(bootstrapError instanceof ApiError)) {
          throw bootstrapError;
        }

        if (bootstrapError.status !== 401) {
          throw bootstrapError;
        }

        return toUnauthenticatedResult(isAuthDisabled);
      }
    }

    return { kind: "refresh-retry" };
  }
}
