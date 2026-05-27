import { describe, expect, it, vi } from "vitest";

import { BaseApi, joinApiPath, type ApiClient } from "@/shared/api";

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

class TestApi extends BaseApi {
  constructor(apiClient: ApiClient, basePath?: string) {
    super(apiClient, { basePath });
  }

  read(path: string, config?: Parameters<ApiClient["get"]>[1]) {
    return this.get(path, config);
  }

  write(path: string, config?: Parameters<ApiClient["post"]>[2]) {
    return this.post(path, undefined, config);
  }
}

describe("BaseApi", () => {
  it("prefixes requests with the configured base path", async () => {
    const client = createApiClientMock();
    vi.mocked(client.get).mockResolvedValue({ ok: true });

    const api = new TestApi(client, "/auth");

    await api.read("/me", { dedupeKey: false });

    expect(client.get).toHaveBeenCalledWith("/auth/me", { dedupeKey: false });
  });

  it("lets feature APIs compose nested path segments through inheritance", async () => {
    const client = createApiClientMock();
    vi.mocked(client.post).mockResolvedValue({ ok: true });

    class PluginActionApi extends BaseApi {
      constructor(apiClient: ApiClient) {
        super(apiClient, { basePath: "/plugins" });
      }

      enable(pluginId: string) {
        return this.post(`/${pluginId}/actions/enable`, undefined, {
          dedupeKey: false,
        });
      }
    }

    const pluginsApi = new PluginActionApi(client);

    await pluginsApi.enable("demo");

    expect(client.post).toHaveBeenCalledWith(
      "/plugins/demo/actions/enable",
      undefined,
      { dedupeKey: false },
    );
  });
});
