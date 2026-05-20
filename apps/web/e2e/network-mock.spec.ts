import { expect, test } from "@playwright/test";

import { mockApiError, mockApiSuccess, mockHttpError } from "./mocks/mockEnvelope";
import { createRouteMock } from "./mocks/route-mock";

test("reuses shared mock helpers for /api/v1 route interception", async ({ page }) => {
  test.setTimeout(90_000);

  const routeMock = createRouteMock(page);

  await routeMock.mockApiRoute(
    "GET",
    "/api/v1/mock-probe",
    mockApiSuccess(
      { source: "route-mock", ok: true },
      { requestId: "req-probe" },
    ),
  );
  await routeMock.mockHttpRoute(
    "GET",
    "/api/v1/mock-http-error",
    mockHttpError({
      status: 503,
      body: mockApiError({
        code: 50_300,
        msg: "temporary outage",
        requestId: "req-http",
      }),
    }),
  );

  await page.goto("/events");

  const successPayload = await page.evaluate(async () => {
    const response = await fetch("/api/v1/mock-probe");

    return response.json();
  });
  const httpFailure = await page.evaluate(async () => {
    const response = await fetch("/api/v1/mock-http-error");

    return {
      body: await response.json(),
      status: response.status,
    };
  });

  expect(successPayload).toEqual({
    code: 0,
    data: {
      ok: true,
      source: "route-mock",
    },
    msg: "ok",
    request_id: "req-probe",
  });
  expect(httpFailure).toEqual({
    status: 503,
    body: {
      code: 50_300,
      data: null,
      msg: "temporary outage",
      request_id: "req-http",
    },
  });
});
