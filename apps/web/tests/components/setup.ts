import { afterMount, beforeMount } from '@playwright/experimental-ct-react/hooks';
import { createElement } from 'react';
import { cleanup } from '@testing-library/react';
import { AppProviders, createAppQueryClient } from '@/app/providers';
import type { RuntimeConfig } from '@/shared/config';
import type { TestProviderHooksConfig } from '@/test/provider-hooks';

const defaultRuntimeConfig: RuntimeConfig = {
  apiBaseUrl: '',
  websocketUrl: '',
  mode: 'test',
  authEnabled: false,
};

beforeMount<TestProviderHooksConfig>(async ({ App, hooksConfig }) => {
  const config = {
    ...defaultRuntimeConfig,
    ...hooksConfig?.runtimeConfig,
  };
  const queryClient = createAppQueryClient();

  return createElement(
    AppProviders,
    { config, queryClient },
    createElement(App),
  );
});

afterMount(async () => {
  cleanup();
});
