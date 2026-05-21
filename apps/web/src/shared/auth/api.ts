import type { ApiClient } from "@/shared/api";

import type { AuthenticatedActor, LoginPayload, LogoutResponse } from "./types";

export function loginWithPassword(
  apiClient: ApiClient,
  payload: LoginPayload,
): Promise<AuthenticatedActor> {
  return apiClient.post<LoginPayload, AuthenticatedActor>(
    "/auth/login",
    payload,
    { skipCsrf: true },
  );
}

export function fetchCurrentActor(
  apiClient: ApiClient,
): Promise<AuthenticatedActor> {
  return apiClient.get<AuthenticatedActor>("/me", { dedupeKey: false });
}

export function logoutSession(apiClient: ApiClient): Promise<LogoutResponse> {
  return apiClient.post<undefined, LogoutResponse>("/auth/logout", undefined, {
    dedupeKey: false,
  });
}
