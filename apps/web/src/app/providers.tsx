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

export function createAppQueryClient(
  config: QueryClientConfig = {},
): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
      },
    },
    ...config,
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
