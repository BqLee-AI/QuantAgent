import { StrictMode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { RouterProvider } from '@tanstack/react-router';
import { AppErrorBoundary, StartupErrorFallback } from './error-boundary';
import { AppProviders, createAppQueryClient } from './providers';
import { createAppRouter } from './router';
import { loadRuntimeConfig, type RuntimeConfig } from '../shared/config';

export interface BootstrapOptions {
  config?: RuntimeConfig;
  queryClient?: ReturnType<typeof createAppQueryClient>;
  router?: ReturnType<typeof createAppRouter>;
}

function toStartupError(error: unknown, fallbackMessage: string): Error {
  return error instanceof Error ? error : new Error(fallbackMessage);
}

function renderStartupError(root: Root, error: Error): void {
  root.render(<StartupErrorFallback error={error} />);
}

export function bootstrapApp(
  container: HTMLElement,
  options: BootstrapOptions = {},
): Root {
  const root = createRoot(container);

  let config: RuntimeConfig;

  try {
    config = options.config ?? loadRuntimeConfig();
  } catch (error) {
    const startupError = toStartupError(
      error,
      'Failed to load runtime config before app bootstrap.',
    );

    renderStartupError(root, startupError);

    return root;
  }

  const queryClient = options.queryClient ?? createAppQueryClient();
  const router = options.router ?? createAppRouter();
  const app = (
    <AppProviders config={config} queryClient={queryClient}>
      <AppErrorBoundary fallback={(error) => <StartupErrorFallback error={error} />}>
        <RouterProvider router={router} />
      </AppErrorBoundary>
    </AppProviders>
  );

  root.render(config.mode === 'production' ? app : <StrictMode>{app}</StrictMode>);

  return root;
}
