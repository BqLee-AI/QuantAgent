import type { AxiosAdapter, AxiosRequestConfig } from "axios";

import type { ApiError } from "./errors";

export interface ApiResponse<T> {
  code: number;
  data: T | null;
  msg: string;
  request_id?: string;
  trace_id?: string;
}

export type ApiMethod = "delete" | "get" | "patch" | "post" | "put";

export interface RequestConfig {
  signal?: AbortSignal;
  timeout?: number;
  headers?: Record<string, string>;
  params?: Record<string, boolean | number | string | null | undefined>;
  dedupeKey?: false | string;
  skipCsrf?: boolean;
}

export interface ApiClientConfig {
  baseURL?: string;
  timeout?: number;
  withCredentials?: boolean;
  headers?: Record<string, string>;
  csrfHeaderName?: string;
  getCsrfToken?: () => null | string | undefined;
  onError?: (error: ApiError) => void;
  onUnauthorized?: (error: ApiError) => void;
  adapter?: AxiosAdapter;
}

export interface RequestOptions<TBody> extends RequestConfig {
  method?: ApiMethod;
  data?: TBody;
}

export interface InternalRequestConfig extends AxiosRequestConfig {
  dedupeKey?: false | string;
  _returnEnvelope?: boolean;
  skipCsrf?: boolean;
}

// TODO: Replace app-local API payloads with generated contract types from @quantagent/contracts.
