import type { ApiClient } from "./client";
import type { ApiResponse, RequestConfig, RequestOptions } from "./types";

export interface BaseApi {
  del<TResponse>(path: string, config?: RequestConfig): Promise<TResponse>;
  get<TResponse>(path: string, config?: RequestConfig): Promise<TResponse>;
  patch<TBody, TResponse>(
    path: string,
    data?: TBody,
    config?: RequestConfig,
  ): Promise<TResponse>;
  post<TBody, TResponse>(
    path: string,
    data?: TBody,
    config?: RequestConfig,
  ): Promise<TResponse>;
  put<TBody, TResponse>(
    path: string,
    data?: TBody,
    config?: RequestConfig,
  ): Promise<TResponse>;
  request<TResponse, TBody = unknown>(
    path: string,
    options?: RequestOptions<TBody>,
  ): Promise<TResponse>;
  requestEnvelope<TResponse, TBody = unknown>(
    path: string,
    options?: RequestOptions<TBody>,
  ): Promise<ApiResponse<TResponse>>;
  withBasePath(basePath: string): BaseApi;
}

export interface BaseApiConfig {
  basePath?: string;
}

function normalizePathSegment(value: string): string {
  return value.replace(/^\/+|\/+$/g, "");
}

export function joinApiPath(basePath: string | undefined, path: string): string {
  const normalizedPath = normalizePathSegment(path);
  const normalizedBasePath = normalizePathSegment(basePath ?? "");

  if (!normalizedBasePath && !normalizedPath) {
    return "/";
  }

  if (!normalizedBasePath) {
    return `/${normalizedPath}`;
  }

  if (!normalizedPath) {
    return `/${normalizedBasePath}`;
  }

  return `/${normalizedBasePath}/${normalizedPath}`;
}

export function createBaseApi(
  apiClient: ApiClient,
  config: BaseApiConfig = {},
): BaseApi {
  const basePath = config.basePath ?? "";
  const resolvePath = (path: string) => joinApiPath(basePath, path);

  return {
    del<TResponse>(path: string, requestConfig?: RequestConfig): Promise<TResponse> {
      return apiClient.del<TResponse>(resolvePath(path), requestConfig);
    },
    get<TResponse>(path: string, requestConfig?: RequestConfig): Promise<TResponse> {
      return apiClient.get<TResponse>(resolvePath(path), requestConfig);
    },
    patch<TBody, TResponse>(
      path: string,
      data?: TBody,
      requestConfig?: RequestConfig,
    ): Promise<TResponse> {
      return apiClient.patch<TBody, TResponse>(resolvePath(path), data, requestConfig);
    },
    post<TBody, TResponse>(
      path: string,
      data?: TBody,
      requestConfig?: RequestConfig,
    ): Promise<TResponse> {
      return apiClient.post<TBody, TResponse>(resolvePath(path), data, requestConfig);
    },
    put<TBody, TResponse>(
      path: string,
      data?: TBody,
      requestConfig?: RequestConfig,
    ): Promise<TResponse> {
      return apiClient.put<TBody, TResponse>(resolvePath(path), data, requestConfig);
    },
    request<TResponse, TBody = unknown>(
      path: string,
      options?: RequestOptions<TBody>,
    ): Promise<TResponse> {
      return apiClient.request<TResponse, TBody>(resolvePath(path), options);
    },
    requestEnvelope<TResponse, TBody = unknown>(
      path: string,
      options?: RequestOptions<TBody>,
    ): Promise<ApiResponse<TResponse>> {
      return apiClient.requestEnvelope<TResponse, TBody>(resolvePath(path), options);
    },
    withBasePath(nextBasePath: string): BaseApi {
      return createBaseApi(apiClient, {
        basePath: joinApiPath(basePath, nextBasePath),
      });
    },
  };
}
