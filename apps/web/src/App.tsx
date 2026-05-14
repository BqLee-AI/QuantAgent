import { Outlet } from '@tanstack/react-router';
import { useRuntimeConfig } from './shared/config';

export default function App() {
  const config = useRuntimeConfig();

  return (
    <main style={{ padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <header>
        <h1>QuantAgent</h1>
        <p>Frontend bootstrap shell is ready.</p>
      </header>

      <section>
        <h2>Runtime config</h2>
        <dl>
          <dt>API base URL</dt>
          <dd>{config.apiBaseUrl}</dd>
          <dt>WebSocket URL</dt>
          <dd>{config.websocketUrl}</dd>
          <dt>Mode</dt>
          <dd>{config.mode}</dd>
          <dt>Auth enabled</dt>
          <dd>{config.authEnabled ? 'yes' : 'no'}</dd>
        </dl>
      </section>

      <Outlet />
    </main>
  );
}
