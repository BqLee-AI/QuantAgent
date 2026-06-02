import type { ApiClient, ApiClientConfig } from "@/shared/api";
import type { PluginConfigApi } from "@/features/plugins";
import type { AuthApi } from "@/shared/auth/api";
import type { ModelProviderApi } from "@/features/models/api";
import type { RuntimeAuditApi } from "@/features/runtime/api";

export type RealtimeStatus = "connected" | "disabled" | "reconnecting";

export interface RealtimeRuntime {
  client: null;
  status: RealtimeStatus;
}

export interface RuntimeApis {
  auth: AuthApi;
  plugins: PluginConfigApi;
  models: ModelProviderApi;
  modelProviders: ModelProviderApi;
  runtimeAudit: RuntimeAuditApi;
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
