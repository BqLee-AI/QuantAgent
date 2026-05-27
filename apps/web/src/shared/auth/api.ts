import { BaseApi, type ApiClient } from "@/shared/api";

import type {
  AuthenticatedActor,
  LoginPayload,
  LogoutResponse,
  RefreshedSession,
} from "./types";

export class AuthApi extends BaseApi {
  constructor(apiClient: ApiClient) {
    super(apiClient, { basePath: "/auth" });
  }

  fetchCurrentActor(): Promise<AuthenticatedActor> {
    return this.apiClient.get<AuthenticatedActor>("/me", { dedupeKey: false });
  }

  loginWithPassword(payload: LoginPayload): Promise<AuthenticatedActor> {
    return this.post<LoginPayload, AuthenticatedActor>("/login", payload, {
      skipCsrf: true,
    });
  }

  logoutSession(): Promise<LogoutResponse> {
    return this.post<undefined, LogoutResponse>("/logout", undefined, {
      dedupeKey: false,
    });
  }

  refreshCurrentSession(): Promise<RefreshedSession> {
    return this.post<undefined, RefreshedSession>("/refresh", undefined, {
      dedupeKey: false,
    });
  }
}

export interface AuthApiContract {
  fetchCurrentActor(): Promise<AuthenticatedActor>;
  loginWithPassword(payload: LoginPayload): Promise<AuthenticatedActor>;
  logoutSession(): Promise<LogoutResponse>;
  refreshCurrentSession(): Promise<RefreshedSession>;
}

export function createAuthApi(apiClient: ApiClient): AuthApi {
  return new AuthApi(apiClient);
}
