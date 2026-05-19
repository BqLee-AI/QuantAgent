import { describe, expect, it } from "vitest";

import { loadRuntimeConfig } from "@/shared/config/runtime";

describe("loadRuntimeConfig", () => {
  it("uses safe defaults when runtime env values are missing", () => {
    const config = loadRuntimeConfig({});

    expect(config).toEqual({
      apiBaseUrl: "",
      websocketUrl: "",
      mode: "test",
      authEnabled: false,
    });
  });

  it("maps valid runtime env values into typed config", () => {
    const config = loadRuntimeConfig({
      MODE: "development",
      VITE_API_BASE_URL: "https://api.example.com",
      VITE_WEBSOCKET_URL: "wss://ws.example.com",
      VITE_AUTH_ENABLED: "true",
    });

    expect(config).toEqual({
      apiBaseUrl: "https://api.example.com",
      websocketUrl: "wss://ws.example.com",
      mode: "development",
      authEnabled: true,
    });
  });

  it("rejects invalid boolean env values", () => {
    expect(() =>
      loadRuntimeConfig({
        MODE: "test",
        VITE_API_BASE_URL: "https://api.example.com",
        VITE_WEBSOCKET_URL: "wss://ws.example.com",
        VITE_AUTH_ENABLED: "yes",
      }),
    ).toThrowError(
      "Invalid boolean runtime config: VITE_AUTH_ENABLED. Expected true, false, 1, or 0.",
    );
  });
});
