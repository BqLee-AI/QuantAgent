import {
  AxiosError,
  AxiosHeaders,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, createApiClient } from "@/shared/api";

type Adapter = NonNullable<AxiosRequestConfig["adapter"]>;

function createEnvelopeResponse<T>(
  config: InternalAxiosRequestConfig,
  data: T,
): AxiosResponse<T> {
  return {
    config,
    data,
    headers: {},
    status: 200,
    statusText: "OK",
  };
}

describe("createApiClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("uses the expected default axios configuration", () => {
    const client = createApiClient();

    expect(client.instance.defaults.baseURL).toBe("/api/v1");
    expect(client.instance.defaults.timeout).toBe(10_000);
    expect(client.instance.defaults.withCredentials).toBe(true);
  });

  it("injects Authorization when auth is enabled", async () => {
    const adapter: Adapter = vi.fn(async (config) =>
      createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      }),
    );

    const client = createApiClient({
      adapter,
      authEnabled: true,
      getAccessToken: () => "test-token",
    });

    await client.get<{ ok: boolean }>("/me");

    const requestConfig = vi.mocked(adapter).mock.calls[0]?.[0];
    const headers = AxiosHeaders.from(requestConfig?.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("does not inject Authorization when auth is disabled", async () => {
    const adapter: Adapter = vi.fn(async (config) =>
      createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      }),
    );

    const client = createApiClient({
      adapter,
      authEnabled: false,
      getAccessToken: () => "test-token",
    });

    await client.get<{ ok: boolean }>("/me");

    const requestConfig = vi.mocked(adapter).mock.calls[0]?.[0];
    const headers = AxiosHeaders.from(requestConfig?.headers);
    expect(headers.get("Authorization")).toBeUndefined();
  });

  it("auto-unpacks successful envelopes", async () => {
    const client = createApiClient({
      adapter: async (config) =>
        createEnvelopeResponse(config, {
          code: 0,
          data: { id: 1, name: "Alice" },
          msg: "ok",
        }),
    });

    const user = await client.get<{ id: number; name: string }>("/me");

    expect(user).toEqual({ id: 1, name: "Alice" });
  });

  it("returns the full envelope when explicitly requested", async () => {
    const client = createApiClient({
      adapter: async (config) =>
        createEnvelopeResponse(config, {
          code: 0,
          data: { id: 1 },
          msg: "ok",
        }),
    });

    const envelope = await client.requestEnvelope<{ id: number }>("/me");

    expect(envelope).toEqual({
      code: 0,
      data: { id: 1 },
      msg: "ok",
    });
  });

  it("turns business errors into ApiError", async () => {
    const client = createApiClient({
      adapter: async (config) =>
        createEnvelopeResponse(config, {
          code: 40_001,
          data: null,
          msg: "参数错误",
          request_id: "req-40001",
        }),
    });

    await expect(client.get("/broken")).rejects.toMatchObject({
      code: 40_001,
      msg: "参数错误",
      requestId: "req-40001",
    });
  });

  it("retries once after a successful 401 refresh", async () => {
    let requestCount = 0;
    const recover = vi.fn(async () => undefined);
    const adapter: Adapter = vi.fn(async (config) => {
      requestCount += 1;

      if (requestCount === 1) {
        throw new AxiosError(
          "Unauthorized",
          "ERR_BAD_REQUEST",
          config,
          undefined,
          {
            config,
            data: {
              code: 401,
              data: null,
              msg: "unauthorized",
            },
            headers: {},
            status: 401,
            statusText: "Unauthorized",
          },
        );
      }

      return createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      });
    });

    const client = createApiClient({
      adapter,
      refreshAccessToken: recover,
    });

    await expect(client.get<{ ok: boolean }>("/refresh")).resolves.toEqual({
      ok: true,
    });
    expect(recover).toHaveBeenCalledTimes(1);
  });

  it("shares one refresh promise across concurrent 401 responses", async () => {
    let attempts = 0;
    const recover = vi.fn(async () => {
      await Promise.resolve();
      return undefined;
    });
    const adapter: Adapter = vi.fn(async (config) => {
      attempts += 1;

      if (attempts <= 2) {
        throw new AxiosError(
          "Unauthorized",
          "ERR_BAD_REQUEST",
          config,
          undefined,
          {
            config,
            data: {
              code: 401,
              data: null,
              msg: "unauthorized",
            },
            headers: {},
            status: 401,
            statusText: "Unauthorized",
          },
        );
      }

      return createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      });
    });

    const client = createApiClient({
      adapter,
      refreshAccessToken: recover,
    });

    await Promise.all([
      client.get<{ ok: boolean }>("/one", { dedupeKey: false }),
      client.get<{ ok: boolean }>("/two", { dedupeKey: false }),
    ]);

    expect(recover).toHaveBeenCalledTimes(1);
  });

  it("calls onUnauthorized when refresh fails", async () => {
    const onUnauthorized = vi.fn();
    const client = createApiClient({
      adapter: async (config) => {
        throw new AxiosError(
          "Unauthorized",
          "ERR_BAD_REQUEST",
          config,
          undefined,
          {
            config,
            data: {
              code: 401,
              data: null,
              msg: "unauthorized",
            },
            headers: {},
            status: 401,
            statusText: "Unauthorized",
          },
        );
      },
      onUnauthorized,
      refreshAccessToken: async () => {
        throw new Error("refresh failed");
      },
    });

    await expect(client.get("/refresh-fail")).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("reuses inflight GET requests by default", async () => {
    const adapter: Adapter = vi.fn(async (config) => {
      await Promise.resolve();

      return createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      });
    });

    const client = createApiClient({ adapter });

    const [first, second] = await Promise.all([
      client.get<{ ok: boolean }>("/same"),
      client.get<{ ok: boolean }>("/same"),
    ]);

    expect(first).toEqual({ ok: true });
    expect(second).toEqual({ ok: true });
    expect(vi.mocked(adapter)).toHaveBeenCalledTimes(1);
  });

  it("passes AbortSignal through to axios", async () => {
    const controller = new AbortController();
    const adapter: Adapter = vi.fn(async (config) =>
      createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      }),
    );

    const client = createApiClient({ adapter });

    await client.get<{ ok: boolean }>("/signal", {
      signal: controller.signal,
    });

    const requestConfig = vi.mocked(adapter).mock.calls[0]?.[0];
    expect(requestConfig?.signal).toBe(controller.signal);
  });
});
