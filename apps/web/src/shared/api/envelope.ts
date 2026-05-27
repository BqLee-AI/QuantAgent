import type { AxiosResponse } from "axios";

import { ApiError, createApiErrorFromEnvelope } from "./errors";
import type { ApiResponse, InternalRequestConfig } from "./types";

export function isApiResponse<T>(value: unknown): value is ApiResponse<T> {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ApiResponse<T>>;

  return (
    typeof candidate.code === "number" &&
    typeof candidate.msg === "string" &&
    "data" in candidate
  );
}

export function normalizeResponse<TResponse>(
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
