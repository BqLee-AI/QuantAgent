import type { BaseApi } from "@/shared/api";

import type {
  AuthenticatedActor,
  LoginPayload,
  LogoutResponse,
  RefreshedSession,
} from "./types";

export interface AuthApi {
  fetchCurrentActor(): Promise<AuthenticatedActor>;
  loginWithPassword(payload: LoginPayload): Promise<AuthenticatedActor>;
  logoutSession(): Promise<LogoutResponse>;
  refreshCurrentSession(): Promise<RefreshedSession>;
}

export function createAuthApi(baseApi: BaseApi): AuthApi {
  const authApi = baseApi.withBasePath("/auth");

  return {
    fetchCurrentActor(): Promise<AuthenticatedActor> {
      return baseApi.get<AuthenticatedActor>("/me", { dedupeKey: false });
    },
    loginWithPassword(payload: LoginPayload): Promise<AuthenticatedActor> {
      return authApi.post<LoginPayload, AuthenticatedActor>("/login", payload, {
        skipCsrf: true,
      });
    },
    logoutSession(): Promise<LogoutResponse> {
      return authApi.post<undefined, LogoutResponse>("/logout", undefined, {
        dedupeKey: false,
      });
    },
    refreshCurrentSession(): Promise<RefreshedSession> {
      return authApi.post<undefined, RefreshedSession>("/refresh", undefined, {
        dedupeKey: false,
      });
    },
  };
}
