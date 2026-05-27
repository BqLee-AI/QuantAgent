import type { ApiClient } from "./client";
import type { ApiResponse, RequestConfig, RequestOptions } from "./types";

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

export class BaseApi {
  protected readonly apiClient: ApiClient;
  protected readonly basePath: string;

  constructor(apiClient: ApiClient, config: BaseApiConfig = {}) {
    this.apiClient = apiClient;
    this.basePath = config.basePath ?? "";
  }

  protected del<TResponse>(
    path: string,
    requestConfig?: RequestConfig,
  ): Promise<TResponse> {
    return this.apiClient.del<TResponse>(this.resolvePath(path), requestConfig);
  }

  protected get<TResponse>(
    path: string,
    requestConfig?: RequestConfig,
  ): Promise<TResponse> {
    return this.apiClient.get<TResponse>(this.resolvePath(path), requestConfig);
  }

  protected patch<TBody, TResponse>(
    path: string,
    data?: TBody,
    requestConfig?: RequestConfig,
  ): Promise<TResponse> {
    return this.apiClient.patch<TBody, TResponse>(
      this.resolvePath(path),
      data,
      requestConfig,
    );
  }

  protected post<TBody, TResponse>(
    path: string,
    data?: TBody,
    requestConfig?: RequestConfig,
  ): Promise<TResponse> {
    return this.apiClient.post<TBody, TResponse>(
      this.resolvePath(path),
      data,
      requestConfig,
    );
  }

  protected put<TBody, TResponse>(
    path: string,
    data?: TBody,
    requestConfig?: RequestConfig,
  ): Promise<TResponse> {
    return this.apiClient.put<TBody, TResponse>(
      this.resolvePath(path),
      data,
      requestConfig,
    );
  }

  protected request<TResponse, TBody = unknown>(
    path: string,
    options?: RequestOptions<TBody>,
  ): Promise<TResponse> {
    return this.apiClient.request<TResponse, TBody>(this.resolvePath(path), options);
  }

  protected requestEnvelope<TResponse, TBody = unknown>(
    path: string,
    options?: RequestOptions<TBody>,
  ): Promise<ApiResponse<TResponse>> {
    return this.apiClient.requestEnvelope<TResponse, TBody>(
      this.resolvePath(path),
      options,
    );
  }

  private resolvePath(path: string): string {
    return joinApiPath(this.basePath, path);
  }
}
