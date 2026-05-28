import type { ApiClient, ApiClientConfig } from "@/shared/api";
import type { AuthApi } from "@/shared/auth/api";

export type RealtimeStatus = "connected" | "disabled" | "reconnecting";

export interface RealtimeRuntime {
  client: null;
  status: RealtimeStatus;
}

export interface RuntimeApis {
  auth: AuthApi;
}

export interface AppRuntime {
  apiClient: ApiClient;
  apis: RuntimeApis;
  realtime: RealtimeRuntime;
}

export interface AuthRuntimeBridge {
  getCsrfToken(): null | string;
  handleApiError(error: Parameters<NonNullable<ApiClientConfig["onError"]>>[0]): void;
  handleUnauthorized(): void;
}
