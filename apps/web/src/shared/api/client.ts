import axios, {
  AxiosHeaders,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";

import {
  ApiError,
  createApiErrorFromEnvelope,
  isApiResponse,
  toApiError,
} from "./errors";
import type {
  ApiClientConfig,
  ApiMethod,
  ApiResponse,
  RequestConfig,
  RequestOptions,
} from "./types";

interface InternalRequestConfig extends AxiosRequestConfig {
  dedupeKey?: false | string;
  _isRetry?: boolean;
  _returnEnvelope?: boolean;
}

export interface ApiClient {
  readonly instance: AxiosInstance;
  del<TResponse>(url: string, config?: RequestConfig): Promise<TResponse>;
  get<TResponse>(url: string, config?: RequestConfig): Promise<TResponse>;
  patch<TBody, TResponse>(
    url: string,
    data?: TBody,
    config?: RequestConfig,
  ): Promise<TResponse>;
  post<TBody, TResponse>(
    url: string,
    data?: TBody,
    config?: RequestConfig,
  ): Promise<TResponse>;
  put<TBody, TResponse>(
    url: string,
    data?: TBody,
    config?: RequestConfig,
  ): Promise<TResponse>;
  request<TResponse, TBody = unknown>(
    url: string,
    options?: RequestOptions<TBody>,
  ): Promise<TResponse>;
  requestEnvelope<TResponse, TBody = unknown>(
    url: string,
    options?: RequestOptions<TBody>,
  ): Promise<ApiResponse<TResponse>>;
}

const DEFAULT_BASE_URL = "/api/v1";
const DEFAULT_TIMEOUT = 10_000;
const DEFAULT_TOKEN_STORAGE_KEYS = [
  "quantagent.access_token",
  "access_token",
  "token",
] as const;

function readFromStorage(
  storage: Storage | undefined,
  keys: readonly string[],
): string | null {
  if (!storage) {
    return null;
  }

  for (const key of keys) {
    const value = storage.getItem(key);

    if (value) {
      return value;
    }
  }

  return null;
}

function getStoredAccessToken(keys: readonly string[]): string | null {
  const localToken = readFromStorage(globalThis.localStorage, keys);

  if (localToken) {
    return localToken;
  }

  return readFromStorage(globalThis.sessionStorage, keys);
}

function getDedupeKey(config: InternalRequestConfig): string | undefined {
  if (config.signal || config.dedupeKey === false) {
    return undefined;
  }

  if (typeof config.dedupeKey === "string" && config.dedupeKey.length > 0) {
    return config.dedupeKey;
  }

  const method = config.method?.toLowerCase();

  if (method !== "get" && method !== "head") {
    return undefined;
  }

  const params =
    config.params && typeof config.params === "object"
      ? JSON.stringify(config.params)
      : "";
  const responseMode = config._returnEnvelope ? "envelope" : "data";

  return `${method}:${config.baseURL ?? ""}:${config.url ?? ""}:${params}:${responseMode}`;
}

function normalizeResponse<TResponse>(
  response: AxiosResponse<ApiResponse<TResponse>>,
  requestConfig: InternalRequestConfig,
): ApiResponse<TResponse> | TResponse {
  if (!isApiResponse<TResponse>(response.data)) {
    throw new ApiError({
      code: response.status,
      msg: "Malformed API response envelope.",
      status: response.status,
      cause: response.data,
    });
  }

  if (requestConfig._returnEnvelope) {
    return response.data;
  }

  if (response.data.code !== 0) {
    throw createApiErrorFromEnvelope(response.data, response.status);
  }

  return response.data.data as TResponse;
}

export function createApiClient(config: ApiClientConfig = {}): ApiClient {
  const inflight = new Map<string, Promise<unknown>>();
  const tokenStorageKeys = config.tokenStorageKeys ?? DEFAULT_TOKEN_STORAGE_KEYS;
  const getAccessToken =
    config.getAccessToken ??
    (() => {
      try {
        return getStoredAccessToken(tokenStorageKeys);
      } catch {
        return null;
      }
    });

  let refreshPromise: Promise<null | string | undefined> | null = null;

  const instance = axios.create({
    adapter: config.adapter,
    baseURL: config.baseURL ?? DEFAULT_BASE_URL,
    headers: config.headers,
    timeout: config.timeout ?? DEFAULT_TIMEOUT,
    withCredentials: config.withCredentials ?? true,
  });

  instance.interceptors.request.use((requestConfig: InternalAxiosRequestConfig) => {
    const headers = AxiosHeaders.from(requestConfig.headers ?? {});

    // TODO: inject X-Request-Id / X-Trace-Id once backend tracing conventions are finalized.
    if (config.authEnabled) {
      const token = getAccessToken();

      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    }

    requestConfig.headers = headers;
    return requestConfig;
  });

  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const requestConfig = error.config as InternalRequestConfig | undefined;
      const apiError = toApiError(error);

      if (
        apiError.status === 401 &&
        requestConfig &&
        !requestConfig._isRetry &&
        config.refreshAccessToken
      ) {
        requestConfig._isRetry = true;

        if (!refreshPromise) {
          refreshPromise = Promise.resolve(config.refreshAccessToken()).finally(() => {
            refreshPromise = null;
          });
        }

        try {
          await refreshPromise;
        } catch {
          config.onUnauthorized?.(apiError);
          config.onError?.(apiError);
          return Promise.reject(apiError);
        }

        return instance.request(requestConfig);
      }

      if (apiError.status === 401) {
        config.onUnauthorized?.(apiError);
      }

      config.onError?.(apiError);
      return Promise.reject(apiError);
    },
  );

  function dispatch<TResponse>(requestConfig: InternalRequestConfig): Promise<TResponse> {
    const dedupeKey = getDedupeKey(requestConfig);

    if (!dedupeKey) {
      return instance
        .request<ApiResponse<TResponse>>(requestConfig)
        .then((response) => normalizeResponse(response, requestConfig) as TResponse);
    }

    const inflightRequest = inflight.get(dedupeKey) as Promise<TResponse> | undefined;

    if (inflightRequest) {
      return inflightRequest;
    }

    const request = instance
      .request<ApiResponse<TResponse>>(requestConfig)
      .then((response) => normalizeResponse(response, requestConfig) as TResponse)
      .finally(() => {
        if (inflight.get(dedupeKey) === request) {
          inflight.delete(dedupeKey);
        }
      });

    inflight.set(dedupeKey, request);
    return request;
  }

  function toRequestConfig<TBody>(
    url: string,
    options: RequestOptions<TBody> = {},
  ): InternalRequestConfig {
    const { method, ...requestConfig } = options;

    return {
      ...requestConfig,
      method: method ?? "get",
      url,
    };
  }

  return {
    instance,
    del<TResponse>(url: string, requestConfig?: RequestConfig): Promise<TResponse> {
      return dispatch<TResponse>({
        ...requestConfig,
        method: "delete",
        url,
      });
    },
    get<TResponse>(url: string, requestConfig?: RequestConfig): Promise<TResponse> {
      return dispatch<TResponse>({
        ...requestConfig,
        method: "get",
        url,
      });
    },
    patch<TBody, TResponse>(
      url: string,
      data?: TBody,
      requestConfig?: RequestConfig,
    ): Promise<TResponse> {
      return dispatch<TResponse>({
        ...requestConfig,
        data,
        method: "patch",
        url,
      });
    },
    post<TBody, TResponse>(
      url: string,
      data?: TBody,
      requestConfig?: RequestConfig,
    ): Promise<TResponse> {
      return dispatch<TResponse>({
        ...requestConfig,
        data,
        method: "post",
        url,
      });
    },
    put<TBody, TResponse>(
      url: string,
      data?: TBody,
      requestConfig?: RequestConfig,
    ): Promise<TResponse> {
      return dispatch<TResponse>({
        ...requestConfig,
        data,
        method: "put",
        url,
      });
    },
    request<TResponse, TBody = unknown>(
      url: string,
      options?: RequestOptions<TBody>,
    ): Promise<TResponse> {
      return dispatch<TResponse>(toRequestConfig(url, options));
    },
    requestEnvelope<TResponse, TBody = unknown>(
      url: string,
      options?: RequestOptions<TBody>,
    ): Promise<ApiResponse<TResponse>> {
      return dispatch<ApiResponse<TResponse>>({
        ...toRequestConfig(url, options),
        _returnEnvelope: true,
      });
    },
  };
}

export const apiClient = createApiClient({
  authEnabled: false,
});

export type { ApiMethod };
