export interface AuthenticatedActor {
  actor_id: string;
  actor_type: string;
  capabilities: string[];
  csrf_token: string;
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

export interface LoginPayload {
  password: string;
}

export interface LogoutResponse {
  cleared: boolean;
}
