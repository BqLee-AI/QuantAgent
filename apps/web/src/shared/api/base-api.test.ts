import { describe, expect, it, vi } from "vitest";

import { createBaseApi, joinApiPath, type ApiClient } from "@/shared/api";

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

describe("joinApiPath", () => {
  it.each([
    ["", "/me", "/me"],
    ["/auth", "login", "/auth/login"],
    ["auth/", "/login", "/auth/login"],
    ["/", "/", "/"],
  ])("joins %s and %s into %s", (basePath, path, expected) => {
    expect(joinApiPath(basePath, path)).toBe(expected);
  });
});

describe("createBaseApi", () => {
  it("prefixes requests with the configured base path", async () => {
    const client = createApiClientMock();
    vi.mocked(client.get).mockResolvedValue({ ok: true });

    const baseApi = createBaseApi(client, { basePath: "/auth" });

    await baseApi.get("/me", { dedupeKey: false });

    expect(client.get).toHaveBeenCalledWith("/auth/me", { dedupeKey: false });
  });

  it("creates nested base APIs for grouped endpoints", async () => {
    const client = createApiClientMock();
    vi.mocked(client.post).mockResolvedValue({ ok: true });

    const pluginsApi = createBaseApi(client)
      .withBasePath("/plugins")
      .withBasePath("/:pluginId/actions");

    await pluginsApi.post("enable", undefined, { dedupeKey: false });

    expect(client.post).toHaveBeenCalledWith(
      "/plugins/:pluginId/actions/enable",
      undefined,
      { dedupeKey: false },
    );
  });
});
