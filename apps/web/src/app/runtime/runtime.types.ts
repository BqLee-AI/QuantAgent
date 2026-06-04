import type { ApiClient, ApiClientConfig } from "@/shared/api";
import type { PluginConfigApi } from "@/features/plugins";
import type { PluginDetailApi } from "@/features/plugins/detail/api/plugin-detail.api";
import type { SourceBindingsApi } from "@/features/plugins/source-bindings/api/source-bindings.api";
import type { AuthApi } from "@/shared/auth/api";
import type { ModelProviderApi } from "@/features/models/api";
import type { RuntimeAuditApi } from "@/features/runtime/api";
import type { EventAuditApi } from "@/features/event-audit/api";

export type RealtimeStatus = "connected" | "disabled" | "reconnecting";

export interface RealtimeRuntime {
  client: null;
  status: RealtimeStatus;
}

export interface RuntimeApis {
  auth: AuthApi;
  plugins: PluginConfigApi;
  pluginDetail: PluginDetailApi;
  sourceBindings: SourceBindingsApi;
  models: ModelProviderApi;
  modelProviders: ModelProviderApi;
  runtimeAudit: RuntimeAuditApi;
  eventAudit: EventAuditApi;
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
