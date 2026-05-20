# API Cookie Session Auth 规格

## MODIFIED Requirements

### Requirement: Public And Protected Route Policy

API routes SHALL use a code-reviewed public allowlist and protect API v1 routes by default.

#### Scenario: System probes and login remain public

- **WHEN** an anonymous client requests `GET /api/v1/health`
- **THEN** the request succeeds without a session

- **WHEN** an anonymous client requests `GET /api/v1/ready`
- **THEN** auth is not required before the readiness probe runs

- **WHEN** an anonymous client requests `GET /api/v1/version`
- **THEN** the request succeeds without a session

- **WHEN** an anonymous client posts valid credentials to `POST /api/v1/auth/login`
- **THEN** the login flow may run without a pre-existing session

#### Scenario: Protected route rejects missing session

- **WHEN** an anonymous client requests an API v1 route that is not in the public allowlist
- **THEN** the response uses HTTP 401
- **AND** the response uses the standard `code/data/msg/error` envelope
- **AND** `error.code` is `UNAUTHORIZED`
- **AND** the error contains a `request_id`

#### Scenario: Business routes are not made public by default

- **WHEN** a new API v1 business route is added
- **THEN** the route is protected unless it is explicitly added to the reviewed public allowlist
- **AND** being a read-only route is not sufficient reason to make it anonymous
- **AND** the route registration boundary is testable without relying only on developer memory

#### Scenario: API v1 route registration requires public or protected classification

- **WHEN** implementation registers a standard API v1 router
- **THEN** the router is classified as public or protected at the shared API v1 registration boundary
- **AND** protected routers receive the default session guard through that boundary or a shared helper covered by registration tests
- **AND** adding a bare `include_router` for a business router does not satisfy the protected-by-default policy
- **AND** adding ad hoc route-level session dependencies without the shared classification boundary does not satisfy the protected-by-default policy

#### Scenario: Logout is protected by default and still requires CSRF

- **WHEN** an anonymous client posts to `POST /api/v1/auth/logout`
- **THEN** the request is rejected as unauthorized before logout succeeds

- **WHEN** an authenticated client posts to `POST /api/v1/auth/logout` without a valid `X-CSRF-Token`
- **THEN** the CSRF guard rejects the request
- **AND** the default session guard is not treated as a replacement for CSRF protection

#### Scenario: Debug routes are not public API

- **WHEN** the API app runs in production
- **THEN** debug-only routes are not registered
- **AND** production OpenAPI does not expose debug-only paths

- **WHEN** the API app runs outside production
- **AND** debug routes are registered
- **THEN** those routes are not added to the public allowlist
- **AND** they require a valid session or the reviewed development auth bypass

#### Scenario: Capability and CSRF guards remain route-level controls

- **WHEN** a protected route requires a specific capability
- **THEN** the default protected route policy does not replace the capability guard
- **AND** an authenticated actor without that capability receives HTTP 403

- **WHEN** a protected cookie-session write route is added
- **THEN** the default protected route policy does not replace the CSRF guard
- **AND** the route still rejects missing or invalid `X-CSRF-Token`
