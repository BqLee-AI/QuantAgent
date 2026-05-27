import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/shared/api";

import type { AuthApiContract } from "./api";
import {
  bootstrapSession,
  loginSession,
  logoutSession,
  refreshSession,
} from "./session-actions";

function createAuthApiMock(): AuthApiContract {
  return {
    fetchCurrentActor: vi.fn(),
    loginWithPassword: vi.fn(),
    logoutSession: vi.fn(),
    refreshCurrentSession: vi.fn(),
  };
}

describe("session actions", () => {
  it("bootstraps authenticated state from the current actor", async () => {
    const authApi = createAuthApiMock();
    vi.mocked(authApi.fetchCurrentActor).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-me",
    });

    await expect(
      bootstrapSession({ authApi, isAuthDisabled: false }),
    ).resolves.toMatchObject({
      kind: "authenticated",
      state: {
        csrfToken: "csrf-me",
        status: "authenticated",
      },
    });
  });

  it("keeps 403 bootstrap as authenticated forbidden state", async () => {
    const authApi = createAuthApiMock();
    vi.mocked(authApi.fetchCurrentActor).mockRejectedValue(
      new ApiError({
        code: 403,
        msg: "forbidden",
        requestId: "req-403",
        status: 403,
      }),
    );

    await expect(
      bootstrapSession({ authApi, isAuthDisabled: false }),
    ).resolves.toMatchObject({
      details: {
        requestId: "req-403",
      },
      kind: "forbidden",
      state: {
        lastForbiddenMessage: "forbidden",
        status: "authenticated",
      },
    });
  });

  it("logs in through auth API and returns authenticated state", async () => {
    const authApi = createAuthApiMock();
    vi.mocked(authApi.loginWithPassword).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-login",
    });

    await expect(
      loginSession(
        { password: "admin-password" },
        { authApi, isAuthDisabled: false },
      ),
    ).resolves.toMatchObject({
      kind: "authenticated",
      state: {
        csrfToken: "csrf-login",
      },
    });
  });

  it("propagates logout failures so caller can still run local cleanup in finally", async () => {
    const authApi = createAuthApiMock();
    vi.mocked(authApi.logoutSession).mockRejectedValue(
      new ApiError({
        code: 500,
        msg: "logout failed",
        status: 500,
      }),
    );

    await expect(
      logoutSession(true, { authApi, isAuthDisabled: false }),
    ).rejects.toMatchObject({
      msg: "logout failed",
    });
  });

  it("maps refresh 401 to unauthenticated state", async () => {
    const authApi = createAuthApiMock();
    vi.mocked(authApi.refreshCurrentSession).mockRejectedValue(
      new ApiError({
        code: 401,
        msg: "unauthorized",
        status: 401,
      }),
    );

    await expect(
      refreshSession({ authApi, isAuthDisabled: false }),
    ).resolves.toMatchObject({
      kind: "unauthenticated",
      state: {
        status: "unauthenticated",
      },
    });
  });

  it("recovers refresh 403 by bootstrapping the current actor and asking provider to retry", async () => {
    const authApi = createAuthApiMock();
    vi.mocked(authApi.refreshCurrentSession).mockRejectedValue(
      new ApiError({
        code: 403,
        msg: "forbidden",
        status: 403,
      }),
    );
    vi.mocked(authApi.fetchCurrentActor).mockResolvedValue({
      actor_id: "local_admin",
      actor_type: "local_single_user",
      capabilities: ["runtime.inspect"],
      csrf_token: "csrf-me",
    });

    await expect(
      refreshSession({ authApi, isAuthDisabled: false }),
    ).resolves.toMatchObject({
      kind: "refresh-forbidden",
      state: {
        csrfToken: "csrf-me",
        status: "authenticated",
      },
    });
  });
});
