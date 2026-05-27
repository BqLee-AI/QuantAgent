import { describe, expect, it } from "vitest";

import {
  createAuthenticatedState,
  createBootstrappingState,
  createUnauthenticatedState,
  isDevelopmentActor,
} from "./state";

describe("auth state factories", () => {
  it("creates bootstrapping state without an actor", () => {
    expect(createBootstrappingState()).toMatchObject({
      actor: null,
      csrfToken: null,
      status: "bootstrapping",
    });
  });

  it("keeps auth disabled only for the local development actor", () => {
    expect(
      createAuthenticatedState(
        {
          actor_id: "local_dev",
          actor_type: "local_single_user",
          capabilities: ["runtime.inspect"],
          csrf_token: "csrf",
        },
        true,
      ),
    ).toMatchObject({
      csrfToken: "csrf",
      isAuthDisabled: true,
      status: "authenticated",
    });

    expect(isDevelopmentActor(null)).toBe(false);
    expect(createUnauthenticatedState(true).isAuthDisabled).toBe(true);
  });
});
