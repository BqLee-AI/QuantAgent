import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/shared/api";

import { fetchCurrentActor, loginWithPassword, logoutSession } from "./api";

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
    const client = createApiClientMock();
    vi.mocked(client.post).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-login",
    });

    await loginWithPassword(client, { password: "admin-password" });

    expect(client.post).toHaveBeenCalledWith(
      "/auth/login",
      { password: "admin-password" },
      { skipCsrf: true },
    );
  });

  it("bootstraps the current actor through /me without request dedupe", async () => {
    const client = createApiClientMock();
    vi.mocked(client.get).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-me",
    });

    await fetchCurrentActor(client);

    expect(client.get).toHaveBeenCalledWith("/me", { dedupeKey: false });
  });

  it("logs out through the shared API client so CSRF injection stays centralized", async () => {
    const client = createApiClientMock();
    vi.mocked(client.post).mockResolvedValue({ cleared: true });

    await logoutSession(client);

    expect(client.post).toHaveBeenCalledWith("/auth/logout", undefined, {
      dedupeKey: false,
    });
  });
});
