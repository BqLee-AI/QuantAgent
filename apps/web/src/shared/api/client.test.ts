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

  it("injects CSRF tokens into protected write requests", async () => {
    const adapter: Adapter = vi.fn(async (config) =>
      createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      }),
    );

    const client = createApiClient({
      adapter,
      getCsrfToken: () => "csrf-test-token",
    });

    await client.post<{ name: string }, { ok: boolean }>("/items", { name: "demo" });

    const requestConfig = vi.mocked(adapter).mock.calls[0]?.[0];
    const headers = AxiosHeaders.from(requestConfig?.headers);
    expect(headers.get("X-CSRF-Token")).toBe("csrf-test-token");
  });

  it("does not inject CSRF tokens into read requests", async () => {
    const adapter: Adapter = vi.fn(async (config) =>
      createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      }),
    );

    const client = createApiClient({
      adapter,
      getCsrfToken: () => "csrf-test-token",
    });

    await client.get<{ ok: boolean }>("/me");

    const requestConfig = vi.mocked(adapter).mock.calls[0]?.[0];
    const headers = AxiosHeaders.from(requestConfig?.headers);
    expect(headers.get("X-CSRF-Token")).toBeUndefined();
  });

  it("allows callers to skip CSRF injection for login", async () => {
    const adapter: Adapter = vi.fn(async (config) =>
      createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      }),
    );

    const client = createApiClient({
      adapter,
      getCsrfToken: () => "csrf-test-token",
    });

    await client.post<{ password: string }, { ok: boolean }>(
      "/auth/login",
      { password: "secret" },
      { skipCsrf: true },
    );

    const requestConfig = vi.mocked(adapter).mock.calls[0]?.[0];
    const headers = AxiosHeaders.from(requestConfig?.headers);
    expect(headers.get("X-CSRF-Token")).toBeUndefined();
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

  it("returns the full envelope even when the business code is non-zero", async () => {
    const client = createApiClient({
      adapter: async (config) =>
        createEnvelopeResponse(config, {
          code: 40_001,
          data: null,
          msg: "参数错误",
          request_id: "req-envelope",
        }),
    });

    const envelope = await client.requestEnvelope<null>("/broken");

    expect(envelope).toEqual({
      code: 40_001,
      data: null,
      msg: "参数错误",
      request_id: "req-envelope",
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

  it("calls onUnauthorized when requests return 401", async () => {
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
    });

    await expect(client.get("/unauthorized")).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("does not replay 401 responses through refresh token flows", async () => {
    const onError = vi.fn();
    const onUnauthorized = vi.fn();
    const adapter: Adapter = vi.fn(async (config) => {
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
    });

    const client = createApiClient({
      adapter,
      onError,
      onUnauthorized,
    });

    await expect(client.get("/session-expired")).rejects.toMatchObject({
      code: 401,
      msg: "unauthorized",
      status: 401,
    });
    expect(vi.mocked(adapter)).toHaveBeenCalledTimes(1);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledTimes(1);
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

  it.each([
    {
      method: "post",
      invoke: (
        client: ReturnType<typeof createApiClient>,
        config?: Parameters<ReturnType<typeof createApiClient>["post"]>[2],
      ) => client.post<{ name: string }, { ok: boolean }>("/items", { name: "demo" }, config),
    },
    {
      method: "put",
      invoke: (
        client: ReturnType<typeof createApiClient>,
        config?: Parameters<ReturnType<typeof createApiClient>["put"]>[2],
      ) => client.put<{ name: string }, { ok: boolean }>("/items/1", { name: "demo" }, config),
    },
    {
      method: "patch",
      invoke: (
        client: ReturnType<typeof createApiClient>,
        config?: Parameters<ReturnType<typeof createApiClient>["patch"]>[2],
      ) => client.patch<{ name: string }, { ok: boolean }>("/items/1", { name: "demo" }, config),
    },
    {
      method: "delete",
      invoke: (
        client: ReturnType<typeof createApiClient>,
        config?: Parameters<ReturnType<typeof createApiClient>["del"]>[1],
      ) => client.del<{ ok: boolean }>("/items/1", config),
    },
  ])("$method requests unwrap success envelopes and preserve request config", async ({ invoke }) => {
    const controller = new AbortController();
    const adapter: Adapter = vi.fn(async (config) =>
      createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      }),
    );

    const client = createApiClient({
      adapter,
      getCsrfToken: () => "csrf-test-token",
    });

    await expect(invoke(client, { signal: controller.signal })).resolves.toEqual({
      ok: true,
    });

    const requestConfig = vi.mocked(adapter).mock.calls[0]?.[0];
    const headers = AxiosHeaders.from(requestConfig?.headers);
    expect(headers.get("X-CSRF-Token")).toBe("csrf-test-token");
    expect(requestConfig?.signal).toBe(controller.signal);
  });

  it.each([
    {
      method: "post",
      invoke: (client: ReturnType<typeof createApiClient>) =>
        client.post<{ name: string }, { ok: boolean }>("/items", { name: "demo" }),
    },
    {
      method: "put",
      invoke: (client: ReturnType<typeof createApiClient>) =>
        client.put<{ name: string }, { ok: boolean }>("/items/1", { name: "demo" }),
    },
    {
      method: "patch",
      invoke: (client: ReturnType<typeof createApiClient>) =>
        client.patch<{ name: string }, { ok: boolean }>("/items/1", { name: "demo" }),
    },
    {
      method: "delete",
      invoke: (client: ReturnType<typeof createApiClient>) =>
        client.del<{ ok: boolean }>("/items/1"),
    },
  ])("$method requests turn business errors into ApiError", async ({ invoke }) => {
    const client = createApiClient({
      adapter: async (config) =>
        createEnvelopeResponse(config, {
          code: 40_001,
          data: null,
          msg: "参数错误",
          request_id: "req-non-get",
        }),
    });

    await expect(invoke(client)).rejects.toMatchObject({
      code: 40_001,
      msg: "参数错误",
      requestId: "req-non-get",
    });
  });

  it.each([
    {
      method: "post",
      run: (client: ReturnType<typeof createApiClient>) =>
        Promise.all([
          client.post<{ name: string }, { created: boolean }>("/items", { name: "item-1" }),
          client.post<{ name: string }, { created: boolean }>("/items", { name: "item-2" }),
        ]),
    },
    {
      method: "put",
      run: (client: ReturnType<typeof createApiClient>) =>
        Promise.all([
          client.put<{ name: string }, { created: boolean }>("/items/1", { name: "item-1" }),
          client.put<{ name: string }, { created: boolean }>("/items/1", { name: "item-2" }),
        ]),
    },
    {
      method: "patch",
      run: (client: ReturnType<typeof createApiClient>) =>
        Promise.all([
          client.patch<{ name: string }, { created: boolean }>("/items/1", { name: "item-1" }),
          client.patch<{ name: string }, { created: boolean }>("/items/1", { name: "item-2" }),
        ]),
    },
    {
      method: "delete",
      run: (client: ReturnType<typeof createApiClient>) =>
        Promise.all([
          client.del<{ created: boolean }>("/items/1"),
          client.del<{ created: boolean }>("/items/1"),
        ]),
    },
  ])("$method requests are not deduplicated by default", async ({ run }) => {
    const adapter: Adapter = vi.fn(async (config) => {
      await Promise.resolve();
      return createEnvelopeResponse(config, {
        code: 0,
        data: { created: true },
        msg: "ok",
      });
    });

    const client = createApiClient({ adapter });

    await run(client);

    expect(vi.mocked(adapter)).toHaveBeenCalledTimes(2);
  });

  it("does not deduplicate data and envelope GET callers together", async () => {
    const adapter: Adapter = vi.fn(async (config) => {
      await Promise.resolve();
      return createEnvelopeResponse(config, {
        code: 0,
        data: { ok: true },
        msg: "ok",
      });
    });

    const client = createApiClient({ adapter });

    const [data, envelope] = await Promise.all([
      client.get<{ ok: boolean }>("/same"),
      client.requestEnvelope<{ ok: boolean }>("/same"),
    ]);

    expect(data).toEqual({ ok: true });
    expect(envelope).toEqual({
      code: 0,
      data: { ok: true },
      msg: "ok",
    });
    expect(vi.mocked(adapter)).toHaveBeenCalledTimes(2);
  });
});
