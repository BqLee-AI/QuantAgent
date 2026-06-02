import { createApiClient } from "@/shared/api";
import { PluginConfigApi } from "@/features/plugins";
import { AuthApi } from "@/shared/auth/api";
import type { RuntimeConfig } from "@/shared/config";
import { createModelProviderApi } from "@/features/models/api";
import { createRuntimeAuditApi } from "@/features/runtime/api";

import type { AppRuntime, AuthRuntimeBridge } from "./runtime.types";

export interface CreateAppRuntimeOptions {
  auth: AuthRuntimeBridge;
  config: RuntimeConfig;
}

export function createAppRuntime({
  auth,
  config,
}: CreateAppRuntimeOptions): AppRuntime {
  const apiClient = createApiClient({
    baseURL: config.apiBaseUrl || undefined,
    getCsrfToken: auth.getCsrfToken,
    onError: auth.handleApiError,
    onUnauthorized: auth.handleUnauthorized,
    withCredentials: true,
  });
  const modelProviderApi = createModelProviderApi(apiClient);
  const runtimeAuditApi = createRuntimeAuditApi(apiClient);

  return {
    apiClient,
    apis: {
      auth: new AuthApi(apiClient),
      plugins: new PluginConfigApi(apiClient),
      models: modelProviderApi,
      // 中文注释：兼容当前 PR 分支里仍在使用 `modelProviders` 的调用点，避免一次重构同时打断旧引用。
      modelProviders: modelProviderApi,
      runtimeAudit: runtimeAuditApi,
    },
    realtime: {
      client: null,
      status: "disabled",
    },
  };
}
