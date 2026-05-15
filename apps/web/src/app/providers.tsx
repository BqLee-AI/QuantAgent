import type { PropsWithChildren } from 'react';
import { HeroUIProvider } from '@heroui/system';
import {
  QueryClient,
  QueryClientProvider,
  type QueryClientConfig,
} from '@tanstack/react-query';
import { RuntimeConfigProvider, type RuntimeConfig } from '../shared/config';

export interface AppProvidersProps extends PropsWithChildren {
  config: RuntimeConfig;
  queryClient: QueryClient;
}

function deepMergeRecord(
  base: Record<string, unknown>,
  override: Record<string, unknown>,
): Record<string, unknown> {
  const result: Record<string, unknown> = { ...base };

  for (const [key, value] of Object.entries(override)) {
    const baseValue = result[key];

    if (
      baseValue &&
      value &&
      typeof baseValue === 'object' &&
      typeof value === 'object' &&
      !Array.isArray(baseValue) &&
      !Array.isArray(value)
    ) {
      result[key] = deepMergeRecord(
        baseValue as Record<string, unknown>,
        value as Record<string, unknown>,
      );
      continue;
    }

    result[key] = value;
  }

  return result;
}

export function createAppQueryClient(
  config: QueryClientConfig = {},
): QueryClient {
  const { defaultOptions: customDefaultOptions, ...clientConfig } = config;
  const defaultOptions = deepMergeRecord(
    {
      queries: {
        staleTime: 30_000,
        retry: 1,
      },
    },
    (customDefaultOptions ?? {}) as Record<string, unknown>,
  ) as NonNullable<QueryClientConfig['defaultOptions']>;

  return new QueryClient({
    ...clientConfig,
    defaultOptions,
  });
}

export function AppProviders({
  children,
  config,
  queryClient,
}: AppProvidersProps) {
  return (
    <RuntimeConfigProvider value={config}>
      <HeroUIProvider>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </HeroUIProvider>
    </RuntimeConfigProvider>
  );
}
