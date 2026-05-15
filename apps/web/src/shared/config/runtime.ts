export interface RuntimeConfig {
  apiBaseUrl: string;
  websocketUrl: string;
  mode: string;
  authEnabled: boolean;
}

type RuntimeEnv = {
  MODE?: string;
  VITE_API_BASE_URL?: string;
  VITE_WEBSOCKET_URL?: string;
  VITE_AUTH_ENABLED?: string;
};

function requireValue(value: string | undefined, key: string): string {
  if (!value || value.trim().length === 0) {
    throw new Error(`Missing required runtime config: ${key}`);
  }

  return value.trim();
}

function parseBoolean(value: string | undefined, key: string): boolean {
  const normalized = requireValue(value, key).toLowerCase();

  if (normalized === 'true' || normalized === '1') {
    return true;
  }

  if (normalized === 'false' || normalized === '0') {
    return false;
  }

  throw new Error(
    `Invalid boolean runtime config: ${key}. Expected true, false, 1, or 0.`,
  );
}

export function loadRuntimeConfig(env: RuntimeEnv = import.meta.env): RuntimeConfig {
  return {
    apiBaseUrl: requireValue(env.VITE_API_BASE_URL, 'VITE_API_BASE_URL'),
    websocketUrl: requireValue(env.VITE_WEBSOCKET_URL, 'VITE_WEBSOCKET_URL'),
    mode: requireValue(env.MODE, 'MODE'),
    authEnabled: parseBoolean(env.VITE_AUTH_ENABLED, 'VITE_AUTH_ENABLED'),
  };
}
