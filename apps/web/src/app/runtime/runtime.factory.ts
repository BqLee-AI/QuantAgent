import { createApiClient } from "@/shared/api";
import { PluginConfigApi } from "@/features/plugins";
import { PluginDetailApi } from "@/features/plugins/detail/api/plugin-detail.api";
import { SourceBindingsApi } from "@/features/plugins/source-bindings/api/source-bindings.api";
import { AuthApi } from "@/shared/auth/api";
import type { RuntimeConfig } from "@/shared/config";
import { createModelProviderApi } from "@/features/models/api";
import { createRuntimeAuditApi } from "@/features/runtime/api";
import { createEventAuditApi } from "@/features/event-audit/api";
import { createEventsApi } from "@/features/events/api";

import type { AppRuntime, AuthRuntimeBridge } from "./runtime.types";

export interface CreateAppRuntimeOptions {
  auth: AuthRuntimeBridge;
  config: RuntimeConfig;
}

export function createAppRuntime({ auth, config }: CreateAppRuntimeOptions): AppRuntime {
  const apiClient = createApiClient({
    baseURL: config.apiBaseUrl || undefined,
    getCsrfToken: auth.getCsrfToken,
    onError: auth.handleApiError,
    onUnauthorized: auth.handleUnauthorized,
    withCredentials: true,
  });
  const modelProviderApi = createModelProviderApi(apiClient);
  const runtimeAuditApi = createRuntimeAuditApi(apiClient);
  const eventAuditApi = createEventAuditApi(apiClient);
  const eventsApi = createEventsApi(apiClient);

  return {
    apiClient,
    apis: {
      auth: new AuthApi(apiClient),
      plugins: new PluginConfigApi(apiClient),
      pluginDetail: new PluginDetailApi(apiClient),
      sourceBindings: new SourceBindingsApi(apiClient),
      models: modelProviderApi,
      // 中文注释：兼容当前 PR 分支里仍在使用 `modelProviders` 的调用点，避免一次重构同时打断旧引用。
      modelProviders: modelProviderApi,
      runtimeAudit: runtimeAuditApi,
      eventAudit: eventAuditApi,
      events: eventsApi,
    },
    realtime: {
      client: null,
      status: "disabled",
    },
  };
}
