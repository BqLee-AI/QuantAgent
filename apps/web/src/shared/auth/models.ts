export interface AuthenticatedActor {
  actor_id: string;
  actor_type: string;
  capabilities: string[];
  csrf_token: string;
}

export interface RefreshedSession extends AuthenticatedActor {
  expires_at: number;
  max_expires_at: number;
}

export type AuthStatus = "authenticated" | "bootstrapping" | "unauthenticated";

export interface ForbiddenDetails {
  message: string;
  requestId: null | string;
  traceId: null | string;
}

export interface AuthState {
  actor: AuthenticatedActor | null;
  capabilities: Set<string>;
  csrfToken: string | null;
  forbidden: ForbiddenDetails | null;
  isAuthDisabled: boolean;
  lastForbiddenMessage: string | null;
  status: AuthStatus;
}

export interface AuthContextValue extends AuthState {
  bootstrap(): Promise<void>;
  login(password: string): Promise<void>;
  logout(): Promise<void>;
}

export interface LoginPayload {
  password: string;
}

export interface LogoutResponse {
  cleared: boolean;
}
