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

const DEFAULT_RUNTIME_CONFIG: RuntimeConfig = {
  apiBaseUrl: '',
  websocketUrl: '',
  mode: 'test',
  authEnabled: false,
};

function readValue(value: string | undefined, fallback: string): string {
  return value?.trim() || fallback;
}

function parseBoolean(
  value: string | undefined,
  fallback: boolean,
  configName: string,
): boolean {
  if (value === undefined || value.trim().length === 0) {
    return fallback;
  }

  const normalized = value.trim().toLowerCase();

  if (normalized === 'true' || normalized === '1') {
    return true;
  }

  if (normalized === 'false' || normalized === '0') {
    return false;
  }

  throw new Error(
    `Invalid boolean runtime config: ${configName}. Expected true, false, 1, or 0.`,
  );
}

export function loadRuntimeConfig(env: RuntimeEnv = import.meta.env): RuntimeConfig {
  return {
    apiBaseUrl: readValue(env.VITE_API_BASE_URL, DEFAULT_RUNTIME_CONFIG.apiBaseUrl),
    websocketUrl: readValue(
      env.VITE_WEBSOCKET_URL,
      DEFAULT_RUNTIME_CONFIG.websocketUrl,
    ),
    mode: readValue(env.MODE, DEFAULT_RUNTIME_CONFIG.mode),
    authEnabled: parseBoolean(
      env.VITE_AUTH_ENABLED,
      DEFAULT_RUNTIME_CONFIG.authEnabled,
      'VITE_AUTH_ENABLED',
    ),
  };
}
