import type { AuthenticatedActor, AuthState } from "./models";

const DEVELOPMENT_ACTOR_ID = "local_dev";

export function isDevelopmentActor(actor: AuthenticatedActor | null): boolean {
  return actor?.actor_id === DEVELOPMENT_ACTOR_ID;
}

export function createUnauthenticatedState(isAuthDisabled: boolean): AuthState {
  return {
    actor: null,
    capabilities: new Set<string>(),
    csrfToken: null,
    forbidden: null,
    isAuthDisabled,
    lastForbiddenMessage: null,
    status: "unauthenticated",
  };
}

export function createBootstrappingState(): AuthState {
  return {
    ...createUnauthenticatedState(false),
    status: "bootstrapping",
  };
}

export function createAuthenticatedState(
  actor: AuthenticatedActor,
  isAuthDisabled: boolean,
): AuthState {
  return {
    actor,
    capabilities: new Set(actor.capabilities),
    csrfToken: actor.csrf_token,
    forbidden: null,
    isAuthDisabled: isAuthDisabled && isDevelopmentActor(actor),
    lastForbiddenMessage: null,
    status: "authenticated",
  };
}
