import { describe, expect, it, vi } from "vitest";

import type { BaseApi } from "@/shared/api";

import { createAuthApi } from "./api";

function createBaseApiMock(): BaseApi {
  return {
    del: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    request: vi.fn(),
    requestEnvelope: vi.fn(),
    withBasePath: vi.fn(),
  };
}

describe("auth API helpers", () => {
  it("logs in without CSRF because no session exists yet", async () => {
    const baseApi = createBaseApiMock();
    const authBaseApi = createBaseApiMock();
    vi.mocked(baseApi.withBasePath).mockReturnValue(authBaseApi);
    vi.mocked(authBaseApi.post).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-login",
    });
    const authApi = createAuthApi(baseApi);

    await authApi.loginWithPassword({ password: "admin-password" });

    expect(authBaseApi.post).toHaveBeenCalledWith(
      "/login",
      { password: "admin-password" },
      { skipCsrf: true },
    );
  });

  it("bootstraps the current actor through /me without request dedupe", async () => {
    const baseApi = createBaseApiMock();
    vi.mocked(baseApi.withBasePath).mockReturnValue(createBaseApiMock());
    vi.mocked(baseApi.get).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-me",
    });
    const authApi = createAuthApi(baseApi);

    await authApi.fetchCurrentActor();

    expect(baseApi.get).toHaveBeenCalledWith("/me", { dedupeKey: false });
  });

  it("logs out through the shared API client so CSRF injection stays centralized", async () => {
    const baseApi = createBaseApiMock();
    const authBaseApi = createBaseApiMock();
    vi.mocked(baseApi.withBasePath).mockReturnValue(authBaseApi);
    vi.mocked(authBaseApi.post).mockResolvedValue({ cleared: true });
    const authApi = createAuthApi(baseApi);

    await authApi.logoutSession();

    expect(authBaseApi.post).toHaveBeenCalledWith("/logout", undefined, {
      dedupeKey: false,
    });
  });

  it("refreshes the current session through the explicit refresh endpoint", async () => {
    const baseApi = createBaseApiMock();
    const authBaseApi = createBaseApiMock();
    vi.mocked(baseApi.withBasePath).mockReturnValue(authBaseApi);
    vi.mocked(authBaseApi.post).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-refresh",
      expires_at: 1_700_000_000,
      max_expires_at: 1_700_003_600,
    });
    const authApi = createAuthApi(baseApi);

    await authApi.refreshCurrentSession();

    expect(authBaseApi.post).toHaveBeenCalledWith("/refresh", undefined, {
      dedupeKey: false,
    });
  });
});
