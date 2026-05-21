# Web App Testing

`apps/web` uses three distinct test layers. Keep the target under the lightest runner that matches the behavior you need to prove.

## Commands

- `bun run --cwd apps/web test:browser:install`: install the Chromium browser set required by the repo-local Playwright CLI.
- `bun run --cwd apps/web test:browser:install:deps`: install the same browser set plus Linux system dependencies via `--with-deps`.
- `bun run --cwd apps/web test:e2e`: run the Chromium smoke test in headless mode.
- `bun run --cwd apps/web test:e2e:ui`: open the Playwright UI for local browser-test debugging.
- `bun run --cwd apps/web test:e2e:debug`: run the Chromium E2E project with the Playwright debugger.
- `bun run --cwd apps/web test:ct`: run the Playwright Component Testing project.
- `bun run --cwd apps/web test:unit`: run Node-only Vitest unit tests.

## Directory Boundaries

- `src/**/*.test.ts`: Vitest Node tests for pure TypeScript logic, data transforms, and modules that do not need a browser.
- `e2e/**/*.spec.ts`: Playwright page-level browser tests that boot the Vite app through the local `test:e2e` wrapper.
- `tests/components/**/*.spec.tsx`: Playwright Component Testing files for browser-backed component rendering and interaction.
  Prefer `src/test/render` for provider-aligned component mounting instead of hand-writing app providers in each test.
- `e2e/mocks/`: reserved for route mock helpers that issue `#55` will add later.

## Runner Boundaries

- Use Vitest when the subject is pure logic and should not depend on DOM rendering, routing, or browser APIs.
- Use Playwright E2E when the subject is real page rendering, navigation, browser APIs, or app-shell behavior.
- Use Playwright Component Testing when the subject is a component that needs a browser environment but not a full page flow.

## Notes

- Local single-user login uses the backend Cookie Session contract:
  `POST /api/v1/auth/login`, `GET /api/v1/me`, and
  `POST /api/v1/auth/logout`.
- The browser owns the HttpOnly session cookie. Frontend auth state only keeps
  actor metadata, capabilities, `csrf_token`, and non-sensitive status flags.
- Protected writes and logout use `X-CSRF-Token` through `src/shared/api`;
  page components should not handwrite auth headers or raw `fetch` calls.
- When `VITE_AUTH_ENABLED=false`, the frontend only enters the dashboard after
  `/me` returns a development actor, and the shell shows an auth-disabled
  development marker.
- The Playwright browser matrix is intentionally Chromium-only for this change.
- In WSL or other mixed Windows/Linux setups, prefer the repo-local install commands above. `bunx playwright install` can populate a Windows-side cache that Linux CT runs cannot use.
- `loadRuntimeConfig()` falls back to test-safe defaults when `VITE_API_BASE_URL`, `VITE_WEBSOCKET_URL`, or `VITE_AUTH_ENABLED` are unset.
- CI browser installation is still out of scope. The current acceptance target is local execution.
- `test:e2e` uses `scripts/run-playwright-e2e.mjs` to start or reuse the Vite dev server and to ensure the process exits cleanly on Windows.
- `playwright.config.ts` owns page-level E2E, while `playwright-ct.config.ts` owns Component Testing so CT-only lifecycle hooks do not leak into E2E runs.
- CT-wide provider wiring and jest-dom matcher setup live under `tests/components/setup.ts` and are loaded through `playwright/index.tsx`.
- The CT project keeps the `@` alias aligned with the main app and intentionally omits the TanStack Router Vite plugin until route-generation compatibility is needed.
