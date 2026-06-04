import { describe, expect, it, vi } from "vitest";

import { createAppRuntime } from "./runtime.factory";

describe("createAppRuntime", () => {
  it("creates a single runtime-scoped api client and api registry", () => {
    const auth = {
      getCsrfToken: vi.fn(() => "csrf-token"),
      handleApiError: vi.fn(),
      handleUnauthorized: vi.fn(),
    };

    const runtime = createAppRuntime({
      auth,
      config: {
        apiBaseUrl: "/api/v1",
        authEnabled: true,
        mode: "test",
        websocketUrl: "",
      },
    });

    expect(runtime.apiClient).toBeDefined();
    expect(runtime.apis.auth).toBeDefined();
    expect(runtime.apis.models).toBeDefined();
    expect(runtime.apis.modelProviders).toBe(runtime.apis.models);
    expect(runtime.apis.plugins).toBeDefined();
    expect(runtime.apis.pluginDetail).toBeDefined();
    expect(runtime.apis.sourceBindings).toBeDefined();
    expect(runtime.apis.runtimeAudit).toBeDefined();
    expect(runtime.realtime).toEqual({
      client: null,
      status: "disabled",
    });
  });
});
