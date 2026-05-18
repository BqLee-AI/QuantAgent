# Web React Testing Library Test Utils Specification

## ADDED Requirements

### Requirement: React Testing Library Dependencies

`apps/web` SHALL provide React Testing Library, jest-dom, and user-event as browser component testing utilities.

#### Scenario: RTL dependencies are available to component tests

- **WHEN** a developer writes a Playwright Component Testing file under `apps/web/tests/components`
- **THEN** the test can import React Testing Library helpers through the web test utility entrypoint
- **AND** the test can use jest-dom matchers
- **AND** the test can use `userEvent` for component interactions.

### Requirement: Shared Render Entrypoint

`apps/web` SHALL expose a shared component test render entrypoint at `apps/web/src/test/render.tsx`.

#### Scenario: Component test renders through shared helper

- **WHEN** a component test needs to render a React component with app providers
- **THEN** it can call `renderWithProviders`
- **AND** the test does not need to handwrite the application provider wrapper
- **AND** common RTL utilities are available from the same entrypoint.

### Requirement: Provider-Aligned Component Rendering

`renderWithProviders` SHALL render components with the production application provider composition by default.

#### Scenario: App providers are reused by default

- **WHEN** a test renders a component with `renderWithProviders`
- **THEN** the component is wrapped by the same app-level provider composition used by `AppProviders`
- **AND** runtime config is available to components that consume it
- **AND** HeroUI and React Query provider boundaries are present.

#### Scenario: Required AppProviders props are constructed internally

- **WHEN** `renderWithProviders` is called
- **THEN** it creates an independent QueryClient instance by calling `createAppQueryClient()`
- **AND** it passes a test-safe RuntimeConfig value to `AppProviders`
- **AND** the test does not need to provide `config` or `queryClient` just to render a component.

#### Scenario: Runtime config can be overridden

- **WHEN** a test needs a non-default runtime config value
- **THEN** `renderWithProviders` accepts a `runtimeConfig?: Partial<RuntimeConfig>` option
- **AND** the override applies only to that render call.

### Requirement: Test-Safe Default RuntimeConfig

`renderWithProviders` SHALL provide a minimal default RuntimeConfig that does not depend on `import.meta.env`.

#### Scenario: Default RuntimeConfig is used without overrides

- **WHEN** a test calls `renderWithProviders` without `runtimeConfig`
- **THEN** the helper uses `{ apiBaseUrl: '', websocketUrl: '', mode: 'test', authEnabled: false }`
- **AND** component rendering does not call `loadRuntimeConfig()` as the default path
- **AND** missing CT environment variables do not prevent rendering.

#### Scenario: RuntimeConfig override merges with defaults

- **WHEN** a test passes `runtimeConfig` with one or more fields
- **THEN** the helper merges those fields over the test-safe defaults
- **AND** unspecified fields keep the default test-safe values.

### Requirement: Minimal renderWithProviders Public API

`renderWithProviders` SHALL expose only the stable options needed by this change.

#### Scenario: Public options stay intentionally narrow

- **WHEN** a developer inspects the `renderWithProviders` options type
- **THEN** it supports at least `runtimeConfig?: Partial<RuntimeConfig>`
- **AND** it returns the same result shape as React Testing Library `render`
- **AND** it does not expose a stable custom QueryClient injection option in this change.

### Requirement: Test State Isolation

`renderWithProviders` SHALL avoid sharing dirty provider state across component tests.

#### Scenario: Provider state is isolated per render

- **WHEN** two component tests call `renderWithProviders`
- **THEN** each render receives independent provider state
- **AND** one test cannot observe cache or runtime config mutation from the other.

#### Scenario: QueryClient public customization remains deferred

- **WHEN** a developer inspects the `renderWithProviders` public API for this change
- **THEN** it does not require or promise a stable custom QueryClient injection option
- **AND** QueryClient customization remains a later design decision.

### Requirement: CT-Scoped Test Setup

jest-dom matcher setup and RTL cleanup SHALL be wired only into the Playwright Component Testing environment.

#### Scenario: CT setup loads matchers and cleanup

- **WHEN** a Playwright CT test runs
- **THEN** jest-dom matchers are registered
- **AND** RTL cleanup runs through the shared setup path.

#### Scenario: Other test layers are not polluted

- **WHEN** Vitest Node unit tests or Playwright E2E tests run
- **THEN** they are not required to load the RTL CT setup
- **AND** their runner responsibilities remain separate.

### Requirement: PlaceholderPanel Helper Proof

The web app SHALL include a minimal component test proving the shared helper works.

#### Scenario: PlaceholderPanel renders through renderWithProviders

- **WHEN** `bun run --cwd apps/web test:ct` executes
- **THEN** `apps/web/tests/components/placeholder-panel-rtl.spec.tsx` renders `PlaceholderPanel` through `renderWithProviders`
- **AND** the test asserts stable rendered content using RTL and jest-dom
- **AND** the existing `apps/web/tests/components/placeholder-panel.spec.tsx` Playwright `mount` proof can remain as a separate CT runner proof
- **AND** the test passes in the Chromium CT project.

### Requirement: Clear Boundary From Other Test Work

This change SHALL remain scoped to component test utilities and not expand into other test infrastructure.

#### Scenario: E2E infrastructure stays owned by #53

- **WHEN** this change is implemented
- **THEN** it does not replace or redesign Playwright E2E infrastructure
- **AND** it continues to build on the existing CT configuration.

#### Scenario: API and network mocking stay out of scope

- **WHEN** this change is implemented
- **THEN** it does not introduce API Client tests
- **AND** it does not introduce a network request mock framework
- **AND** it does not bind the helper to a business page or backend endpoint.

### Requirement: Build And Lint Compatibility

Introducing RTL test utilities SHALL keep existing web checks usable.

#### Scenario: Web checks remain green

- **WHEN** this change is complete
- **THEN** `bun run --cwd apps/web test:ct` passes
- **AND** `bun run lint` passes
- **AND** `bun run build --filter=web` passes.
