import type { MountResult, MountOptions } from '@playwright/experimental-ct-react';
import type { JSX } from 'react';
export {
  cleanup,
  fireEvent,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RuntimeConfig } from '@/shared/config';
import type { TestProviderHooksConfig } from './provider-hooks';

export interface RenderWithProvidersOptions
  extends Omit<MountOptions<TestProviderHooksConfig>, 'hooksConfig'> {
  runtimeConfig?: Partial<RuntimeConfig>;
}

export async function renderWithProviders(
  mount: <HooksConfig>(
    component: JSX.Element,
    options?: MountOptions<HooksConfig>,
  ) => Promise<MountResult>,
  ui: JSX.Element,
  options: RenderWithProvidersOptions = {},
) {
  const { runtimeConfig, ...mountOptions } = options;

  return mount(ui, {
    ...mountOptions,
    hooksConfig: {
      runtimeConfig,
    } satisfies TestProviderHooksConfig,
  });
}

export { userEvent };
