import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/shared/api";

import { AuthApi, createAuthApi } from "./api";

function createApiClientMock(): ApiClient {
  return {
    del: vi.fn(),
    get: vi.fn(),
    instance: {} as ApiClient["instance"],
    patch: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    request: vi.fn(),
    requestEnvelope: vi.fn(),
  };
}

describe("auth API helpers", () => {
  it("logs in without CSRF because no session exists yet", async () => {
    const apiClient = createApiClientMock();
    vi.mocked(apiClient.post).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-login",
    });
    const authApi = createAuthApi(apiClient);

    await authApi.loginWithPassword({ password: "admin-password" });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/auth/login",
      { password: "admin-password" },
      { skipCsrf: true },
    );
  });

  it("bootstraps the current actor through /me without request dedupe", async () => {
    const apiClient = createApiClientMock();
    vi.mocked(apiClient.get).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-me",
    });
    const authApi = createAuthApi(apiClient);

    await authApi.fetchCurrentActor();

    expect(apiClient.get).toHaveBeenCalledWith("/me", { dedupeKey: false });
  });

  it("logs out through the shared API client so CSRF injection stays centralized", async () => {
    const apiClient = createApiClientMock();
    vi.mocked(apiClient.post).mockResolvedValue({ cleared: true });
    const authApi = createAuthApi(apiClient);

    await authApi.logoutSession();

    expect(apiClient.post).toHaveBeenCalledWith("/auth/logout", undefined, {
      dedupeKey: false,
    });
  });

  it("refreshes the current session through the explicit refresh endpoint", async () => {
    const apiClient = createApiClientMock();
    vi.mocked(apiClient.post).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-refresh",
      expires_at: 1_700_000_000,
      max_expires_at: 1_700_003_600,
    });
    const authApi = createAuthApi(apiClient);

    await authApi.refreshCurrentSession();

    expect(apiClient.post).toHaveBeenCalledWith("/auth/refresh", undefined, {
      dedupeKey: false,
    });
  });

  it("exposes a concrete feature API class on top of BaseApi", () => {
    const authApi = new AuthApi(createApiClientMock());

    expect(authApi).toBeInstanceOf(AuthApi);
  });
});
