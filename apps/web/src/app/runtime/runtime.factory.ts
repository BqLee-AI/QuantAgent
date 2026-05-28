import { createApiClient } from "@/shared/api";
import { PluginConfigApi } from "@/features/plugins";
import { AuthApi } from "@/shared/auth/api";
import type { RuntimeConfig } from "@/shared/config";
import { ModelProviderApi } from "@/features/models/api";

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

  return {
    apiClient,
    apis: {
      auth: new AuthApi(apiClient),
      plugins: new PluginConfigApi(apiClient),
      modelProviders: new ModelProviderApi(apiClient),
    },
    realtime: {
      client: null,
      status: "disabled",
    },
  };
}
