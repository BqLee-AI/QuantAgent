import type { Page, Route } from "@playwright/test";

import {
  isMockHttpResponse,
  isMockNetworkFailure,
  type MockHttpResponse,
  type MockNetworkFailure,
} from "./mockEnvelope";
import type { ApiResponse, ApiMethod } from "../../src/shared/api/types";

type MockRouteMethod = Uppercase<ApiMethod>;
type MockRoutePath = RegExp | string;
type MockRouteResult =
  | ApiResponse<unknown>
  | MockHttpResponse
  | MockNetworkFailure;
type MockRouteUrlPattern = string;

interface MockRouteRequest {
  readonly bodyText: null | string;
  readonly headers: Record<string, string>;
  readonly method: MockRouteMethod;
  readonly pathname: string;
  readonly search: string;
  readonly url: string;
}

type MaybePromise<T> = Promise<T> | T;
type MockRouteResponder =
  | MockRouteResult
  | MockRouteResult[]
  | ((request: MockRouteRequest, callCount: number) => MaybePromise<MockRouteResult>);

interface CreateRouteMockOptions {
  routePattern?: MockRouteUrlPattern;
}

function testPattern(pattern: RegExp, value: string): boolean {
  pattern.lastIndex = 0;
  return pattern.test(value);
}

function matchesPath(pathname: string, path: MockRoutePath, search: string): boolean {
  if (typeof path === "string") {
    return pathname === path;
  }

  return testPattern(path, pathname) || testPattern(path, `${pathname}${search}`);
}

function normalizeRequest(route: Route): MockRouteRequest {
  const request = route.request();
  const url = new URL(request.url());

  return {
    bodyText: request.postData(),
    headers: request.headers(),
    method: request.method().toUpperCase() as MockRouteMethod,
    pathname: url.pathname,
    search: url.search,
    url: request.url(),
  };
}

async function resolveMockResult(
  responder: MockRouteResponder,
  request: MockRouteRequest,
  callCount: number,
): Promise<MockRouteResult> {
  if (typeof responder === "function") {
    return responder(request, callCount);
  }

  if (Array.isArray(responder)) {
    const index = Math.min(callCount - 1, responder.length - 1);
    return responder[index] as MockRouteResult;
  }

  return responder;
}

async function fulfillMock(route: Route, result: MockRouteResult): Promise<void> {
  if (isMockNetworkFailure(result)) {
    await route.abort(result.errorCode);
    return;
  }

  if (isMockHttpResponse(result)) {
    await route.fulfill({
      status: result.status,
      headers: {
        "content-type": "application/json",
        ...result.headers,
      },
      body: JSON.stringify(result.body),
    });
    return;
  }

  await route.fulfill({
    status: 200,
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(result),
  });
}

export function createRouteMock(
  page: Page,
  options: CreateRouteMockOptions = {},
) {
  const routePattern = options.routePattern ?? "**/api/v1/**";

  async function registerRoute(
    method: MockRouteMethod,
    path: MockRoutePath,
    responder: MockRouteResponder,
  ): Promise<void> {
    let callCount = 0;

    await page.route(routePattern, async (route) => {
      const request = normalizeRequest(route);

      if (request.method !== method || !matchesPath(request.pathname, path, request.search)) {
        await route.fallback();
        return;
      }

      callCount += 1;
      const result = await resolveMockResult(responder, request, callCount);
      await fulfillMock(route, result);
    });
  }

  return {
    mockApiRoute(
      method: MockRouteMethod,
      path: MockRoutePath,
      responder: MockRouteResponder,
    ) {
      return registerRoute(method, path, responder);
    },
    mockHttpRoute(
      method: MockRouteMethod,
      path: MockRoutePath,
      responder: MockHttpResponse | MockHttpResponse[] | ((request: MockRouteRequest, callCount: number) => MaybePromise<MockHttpResponse>),
    ) {
      return registerRoute(method, path, responder);
    },
    mockNetworkRoute(
      method: MockRouteMethod,
      path: MockRoutePath,
      responder:
        | MockNetworkFailure
        | MockNetworkFailure[]
        | ((request: MockRouteRequest, callCount: number) => MaybePromise<MockNetworkFailure>),
    ) {
      return registerRoute(method, path, responder);
    },
  };
}
