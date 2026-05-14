import { Component, type ErrorInfo, type ReactNode } from 'react';

export interface AppErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface AppErrorBoundaryState {
  error: Error | null;
}

export class AppErrorBoundary extends Component<
  AppErrorBoundaryProps,
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = {
    error: null,
  };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.props.onError?.(error, errorInfo);
  }

  override render(): ReactNode {
    if (this.state.error) {
      return this.props.fallback?.(this.state.error) ?? (
        <StartupErrorFallback error={this.state.error} />
      );
    }

    return this.props.children;
  }
}

export function StartupErrorFallback({ error }: { error?: Error }): ReactNode {
  return (
    <main style={{ padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <h1>QuantAgent 启动失败</h1>
      <p>应用在启动或渲染阶段遇到错误。</p>
      {error ? (
        <pre style={{ whiteSpace: 'pre-wrap' }}>{error.message}</pre>
      ) : null}
    </main>
  );
}
