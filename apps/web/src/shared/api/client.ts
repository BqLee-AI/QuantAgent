import axios, {
  AxiosHeaders,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";

import {
  CSRF_METHODS,
  DEFAULT_API_BASE_URL,
  DEFAULT_API_TIMEOUT_MS,
  DEFAULT_CSRF_HEADER_NAME,
} from "./client-config";
import { getDedupeKey } from "./dedupe";
import { normalizeResponse } from "./envelope";
import {
  ApiError,
  createApiErrorFromEnvelope,
  toApiError,
} from "./errors";
import type {
  ApiClientConfig,
  ApiMethod,
  ApiResponse,
  InternalRequestConfig,
  RequestConfig,
  RequestOptions,
  StreamRequestOptions,
} from "./types";

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
  stream<TBody = unknown>(
    url: string,
    options?: StreamRequestOptions<TBody>,
  ): Promise<Response>;
}

export function createApiClient(config: ApiClientConfig = {}): ApiClient {
  const inflight = new Map<string, Promise<unknown>>();

  const instance = axios.create({
    adapter: config.adapter,
    baseURL: config.baseURL ?? DEFAULT_API_BASE_URL,
    headers: config.headers,
    timeout: config.timeout ?? DEFAULT_API_TIMEOUT_MS,
    withCredentials: config.withCredentials ?? true,
  });

  instance.interceptors.request.use((requestConfig: InternalAxiosRequestConfig) => {
    const headers = AxiosHeaders.from(requestConfig.headers ?? {});
    const internalConfig = requestConfig as InternalRequestConfig;
    const method = requestConfig.method?.toLowerCase() ?? "get";
    const csrfToken = config.getCsrfToken?.();

    // TODO: inject X-Request-Id / X-Trace-Id once backend tracing conventions are finalized.
    if (!internalConfig.skipCsrf && csrfToken && CSRF_METHODS.has(method)) {
      headers.set(config.csrfHeaderName ?? DEFAULT_CSRF_HEADER_NAME, csrfToken);
    }

    requestConfig.headers = headers;
    return requestConfig;
  });

  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const apiError = toApiError(error);

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

  async function stream<TBody = unknown>(
    url: string,
    options: StreamRequestOptions<TBody> = {},
  ): Promise<Response> {
    const { data, headers, method, params, signal, timeout: _timeout, dedupeKey: _dedupeKey, skipCsrf: _skipCsrf } = options;
    const requestHeaders = new Headers(headers);
    const csrfToken = config.getCsrfToken?.();
    if (!_skipCsrf && csrfToken) {
      requestHeaders.set(config.csrfHeaderName ?? DEFAULT_CSRF_HEADER_NAME, csrfToken);
    }
    requestHeaders.set("Accept", "text/event-stream");
    requestHeaders.set("Content-Type", "application/json");

    const response = await fetch(resolveFetchUrl(String(instance.defaults.baseURL ?? DEFAULT_API_BASE_URL), url, params), {
      body: data === undefined ? undefined : JSON.stringify(data),
      credentials: instance.defaults.withCredentials ? "include" : "same-origin",
      headers: requestHeaders,
      method: method ?? "post",
      signal,
    });

    if (response.status === 401) {
      const apiError = await responseToApiError(response);
      config.onUnauthorized?.(apiError);
      config.onError?.(apiError);
      throw apiError;
    }
    if (!response.ok) {
      const apiError = await responseToApiError(response);
      config.onError?.(apiError);
      throw apiError;
    }
    return response;
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
    stream,
  };
}

export type { ApiMethod };

async function responseToApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiResponse<unknown>;
    if (body && typeof body.code === "number" && typeof body.msg === "string") {
      return createApiErrorFromEnvelope(body, response.status);
    }
  } catch {
    // fall through to generic HTTP error
  }
  return new ApiError({
    code: response.status,
    msg: response.statusText || "Streaming request failed.",
    status: response.status,
  });
}

function resolveFetchUrl(
  baseURL: string,
  url: string,
  params?: RequestConfig["params"],
): string {
  const normalizedBase = baseURL.replace(/\/+$/u, "");
  const normalizedPath = url.startsWith("/") ? url : `/${url}`;
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === null || value === undefined) continue;
    query.set(key, String(value));
  }

  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  return `${normalizedBase}${normalizedPath}${suffix}`;
}
