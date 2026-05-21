import React, { StrictMode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { RouterProvider } from '@tanstack/react-router';
import {
  AppErrorBoundary,
  AppErrorScreen,
  createAppErrorDetails,
} from './error-boundary';
import { AppProviders, createAppQueryClient } from './providers';
import { createAppRouter } from './router';
import { useAuth } from '../shared/auth';
import { loadRuntimeConfig, type RuntimeConfig } from '../shared/config';

export interface BootstrapOptions {
  config?: RuntimeConfig;
  queryClient?: ReturnType<typeof createAppQueryClient>;
  router?: ReturnType<typeof createAppRouter>;
}

function toStartupError(error: unknown, fallbackMessage: string): Error {
  return error instanceof Error ? error : new Error(fallbackMessage);
}

function renderStartupError(root: Root, error: Error, description: string): void {
  root.render(
    <AppErrorScreen
      title="QuantAgent 启动失败"
      description={description}
      error={createAppErrorDetails(error)}
    />,
  );
}

function AuthenticatedRouterProvider({
  router,
}: {
  router: ReturnType<typeof createAppRouter>;
}) {
  const auth = useAuth();

  React.useEffect(() => {
    void router.invalidate();
  }, [auth.status, auth.actor?.actor_id, router]);

  return (
    <RouterProvider
      router={router}
      context={{
        auth: {
          capabilities: auth.capabilities,
          status: auth.status,
        },
        capabilities: auth.capabilities,
      }}
    />
  );
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

    renderStartupError(
      root,
      startupError,
      '应用在启动或初始化阶段遇到错误。',
    );

    return root;
  }

  try {
    const queryClient = options.queryClient ?? createAppQueryClient();
    const router = options.router ?? createAppRouter();
    const app = (
      <AppProviders config={config} queryClient={queryClient}>
        <AppErrorBoundary
          fallback={(error) => (
            <AppErrorScreen
              title="QuantAgent 遇到错误"
              description="应用在渲染时发生异常。"
              error={error}
            />
          )}
        >
          <AuthenticatedRouterProvider router={router} />
        </AppErrorBoundary>
      </AppProviders>
    );

    root.render(config.mode === 'production' ? app : <StrictMode>{app}</StrictMode>);
  } catch (error) {
    const startupError = toStartupError(
      error,
      'Failed to initialize the app shell before bootstrap.',
    );

    renderStartupError(
      root,
      startupError,
      '应用在启动或初始化阶段遇到错误。',
    );
  }

  return root;
}
