# Route Mock Extension Point

This directory holds shared network mock utilities introduced by issue `#55`.

## Boundaries

- `mockEnvelope.ts`: pure data envelope builders with no Playwright dependency
- `route-mock.ts`: Playwright `page.route` adapter that reuses `mockEnvelope.ts`
- page-level browser tests stay in `../`

## Consumers

- `apps/web/e2e/**`: browser tests should reuse both helpers directly
- `apps/web/tests/**` and `apps/web/src/**/*.test.ts`: may import `mockEnvelope.ts` when they need the same response envelope semantics without browser runtime

## Scope

- HTTP error means a server response with HTTP status and response body
- network failure means request-layer failure such as `route.abort(...)`
- 401 recover helpers only reserve scenario entry points; they do not implement real refresh endpoint, cookie behavior, or request replay
