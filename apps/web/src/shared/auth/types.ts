export interface AuthenticatedActor {
  actor_id: string;
  actor_type: string;
  capabilities: string[];
  csrf_token: string;
}

export type AuthStatus = "authenticated" | "bootstrapping" | "unauthenticated";

export interface AuthState {
  actor: AuthenticatedActor | null;
  capabilities: Set<string>;
  csrfToken: string | null;
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
