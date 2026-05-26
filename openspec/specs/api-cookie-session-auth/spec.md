# API Cookie Session Auth 规格

## Purpose

定义 `apps/api` 本地单用户 Cookie Session 鉴权闭环的稳定行为契约，包括 auth settings、login/logout/me、CurrentActor、capability guard、CSRF guard、401/403 envelope 和 actor/audit context 边界。
## Requirements
### Requirement: API Auth Settings

`apps/api` SHALL provide local single-user cookie session authentication settings with safe production defaults.

#### Scenario: Production rejects disabled auth

- **WHEN** the API app is created with a production environment
- **AND** auth is configured as disabled
- **THEN** app startup or settings validation fails
- **AND** the app does not silently run with anonymous protected routes

#### Scenario: Production uses secure cookie defaults

- **WHEN** the API app is created with a production environment
- **THEN** the session cookie is configured as `HttpOnly`
- **AND** the session cookie is configured as `Secure`
- **AND** the session cookie uses `SameSite=Lax` unless an explicitly reviewed setting says otherwise

#### Scenario: Local Docker compose is not treated as production

- **WHEN** the API app runs under the repository local Docker compose defaults
- **AND** the environment is not explicitly production
- **THEN** the implementation does not claim production secure-cookie behavior from Docker alone
- **AND** production deployment documentation requires explicit production environment settings before relying on production cookie defaults

#### Scenario: Development may disable auth with actor context

- **WHEN** the API app runs in development with auth disabled
- **THEN** protected dependencies resolve a development actor such as `local_dev`
- **AND** the actor context includes a non-empty capability snapshot
- **AND** downstream handlers do not receive an empty actor or anonymous audit context

### Requirement: Public And Protected Route Policy

SHALL 要求 API routes 使用经过代码审核的 public allowlist，并默认保护 API v1 routes。

#### Scenario: 系统探针和登录保持 public

- **WHEN** 匿名客户端请求 `GET /api/v1/health`
- **THEN** 该请求无需 session 即可成功

- **WHEN** 匿名客户端请求 `GET /api/v1/ready`
- **THEN** readiness probe 运行前不要求 auth

- **WHEN** 匿名客户端请求 `GET /api/v1/version`
- **THEN** 该请求无需 session 即可成功

- **WHEN** 匿名客户端向 `POST /api/v1/auth/login` 提交有效凭证
- **THEN** login flow 可以在没有既有 session 的情况下执行

#### Scenario: protected route 拒绝缺失 session 的请求

- **WHEN** 匿名客户端请求未列入 public allowlist 的 API v1 route
- **THEN** 响应使用 HTTP 401
- **AND** 响应使用标准 `code/data/msg/error` envelope
- **AND** `error.code` 为 `UNAUTHORIZED`
- **AND** 错误信息包含 `request_id`

#### Scenario: 业务 routes 不会默认变成 public

- **WHEN** 新增 API v1 business route
- **THEN** 除非该 route 被显式加入已审核的 public allowlist，否则它是 protected
- **AND** 只读 route 不能作为允许匿名访问的充分理由
- **AND** route registration boundary 可以通过测试验证，不能只依赖开发者记忆

#### Scenario: API v1 route registration 要求声明 public 或 protected 分类

- **WHEN** 实现注册标准 API v1 router
- **THEN** 该 router 在共享 API v1 registration boundary 被分类为 public 或 protected
- **AND** protected routers 通过该边界或被 registration tests 覆盖的共享 helper 获得默认 session guard
- **AND** 仅为 business router 添加裸 `include_router` 不满足 protected-by-default policy
- **AND** 在没有共享分类边界的情况下添加临时 route-level session dependencies，不满足 protected-by-default policy

#### Scenario: logout 默认 protected 且仍要求 CSRF

- **WHEN** 匿名客户端请求 `POST /api/v1/auth/logout`
- **THEN** logout 成功前，该请求会以 unauthorized 被拒绝

- **WHEN** 已认证客户端请求 `POST /api/v1/auth/logout`，但未提供有效 `X-CSRF-Token`
- **THEN** CSRF guard 拒绝该请求
- **AND** 默认 session guard 不会被视为 CSRF protection 的替代品

#### Scenario: debug routes 不是 public API

- **WHEN** API app 运行在 production
- **THEN** debug-only routes 不会被注册
- **AND** production OpenAPI 不暴露 debug-only paths

- **WHEN** API app 运行在非 production 环境
- **AND** debug routes 已注册
- **THEN** 这些 routes 不会加入 public allowlist
- **AND** 它们要求有效 session 或经过审核的 development auth bypass

#### Scenario: capability 和 CSRF guards 保持 route-level controls

- **WHEN** protected route 要求特定 capability
- **THEN** 默认 protected route policy 不替代 capability guard
- **AND** 缺少该 capability 的已认证 actor 会收到 HTTP 403

- **WHEN** 新增 protected cookie-session write route
- **THEN** 默认 protected route policy 不替代 CSRF guard
- **AND** 该 route 仍会拒绝缺失或无效的 `X-CSRF-Token`

### Requirement: Login Logout And Me Routes

API SHALL provide minimal auth routes for browser cookie session use.

#### Scenario: Login issues HttpOnly session cookie

- **WHEN** a client posts valid local administrator credentials to `POST /api/v1/auth/login`
- **THEN** the response succeeds using `ApiResponse[T]`
- **AND** the response sets a session cookie
- **AND** the session cookie is `HttpOnly`
- **AND** the response body contains a non-sensitive `csrf_token`
- **AND** the response body does not contain the raw session, cookie value, signing secret, password, or password hash

#### Scenario: Login failure uses unauthorized envelope

- **WHEN** a client posts invalid local administrator credentials to `POST /api/v1/auth/login`
- **THEN** the response uses HTTP 401
- **AND** `error.code` is `UNAUTHORIZED`
- **AND** the response does not reveal whether the password, hash, session secret, or internal credential source exists

#### Scenario: Logout clears session cookie

- **WHEN** an authenticated client posts to `POST /api/v1/auth/logout`
- **THEN** the response succeeds using `ApiResponse[T]`
- **AND** the response clears the session cookie
- **AND** the response body does not contain the raw session or cookie value

#### Scenario: Me returns actor and capabilities

- **WHEN** an authenticated client requests `GET /api/v1/me`
- **THEN** the response succeeds using `ApiResponse[T]`
- **AND** the response contains the current actor id
- **AND** the response contains the actor type
- **AND** the response contains the current capability snapshot
- **AND** the response contains a non-sensitive `csrf_token`
- **AND** the response does not contain session, cookie, signature, password, password hash, secret, private policy, or stack trace data

### Requirement: CurrentActor And Capability Guard

API SHALL expose a reusable current actor dependency and centralized capability guard.

#### Scenario: Valid session resolves current actor

- **WHEN** a protected route receives a valid unexpired session cookie
- **THEN** the auth dependency resolves a current actor
- **AND** the actor id is stable for the local user
- **AND** the actor type indicates local single-user auth
- **AND** the actor has a capability snapshot

#### Scenario: Invalid or expired session is unauthorized

- **WHEN** a protected route receives an invalid or expired session cookie
- **THEN** the response uses HTTP 401
- **AND** `error.code` is `UNAUTHORIZED`
- **AND** the response does not include the submitted cookie, raw session, signing data, or traceback

#### Scenario: Capability set is centralized

- **WHEN** implementation defines initial capabilities
- **THEN** the set includes `runtime.inspect`
- **AND** the set includes `plugin.configure`
- **AND** the set includes `plugin.install`
- **AND** the set includes `secret.manage`
- **AND** the set includes `approval.approve`
- **AND** the set includes `approval.amend`
- **AND** the set includes `broker.dry_run`
- **AND** route handlers do not each define independent capability strings for the same concepts

#### Scenario: Missing capability is forbidden

- **WHEN** an authenticated actor lacks a required capability
- **THEN** the response uses HTTP 403
- **AND** the response uses the standard `code/data/msg/error` envelope
- **AND** `error.code` is `FORBIDDEN`
- **AND** the error contains a `request_id`

### Requirement: CSRF Protection For Cookie Session Writes

Cookie-session write operations SHALL use CSRF protection with a stable header contract.

#### Scenario: CSRF token is returned by login success

- **WHEN** a browser client completes login successfully
- **THEN** the login response contains a `csrf_token`
- **AND** the token retrieval response does not expose the raw session, cookie value, signing secret, or token derivation material

#### Scenario: CSRF token is returned by me

- **WHEN** an authenticated browser client requests `GET /api/v1/me`
- **THEN** the response contains a `csrf_token`
- **AND** the OpenAPI schema and tests identify `csrf_token` as part of the auth bootstrap contract
- **AND** the response does not expose the raw session, cookie value, signing secret, or token derivation material

#### Scenario: Missing CSRF token rejects protected write

- **WHEN** an authenticated client sends a protected write request without `X-CSRF-Token`
- **THEN** the response rejects the request
- **AND** the response uses the standard error envelope
- **AND** the response does not expose expected token material

#### Scenario: Invalid CSRF token rejects protected write

- **WHEN** an authenticated client sends a protected write request with an invalid `X-CSRF-Token`
- **THEN** the response rejects the request
- **AND** the response uses the standard error envelope
- **AND** the response does not echo the submitted token

#### Scenario: Missing CSRF token rejects logout

- **WHEN** an authenticated client sends `POST /api/v1/auth/logout` without `X-CSRF-Token`
- **THEN** the response rejects the request
- **AND** the response uses the standard error envelope
- **AND** the response does not expose expected token material

#### Scenario: Invalid CSRF token rejects logout

- **WHEN** an authenticated client sends `POST /api/v1/auth/logout` with an invalid `X-CSRF-Token`
- **THEN** the response rejects the request
- **AND** the response uses the standard error envelope
- **AND** the response does not echo the submitted token

#### Scenario: Valid CSRF token allows logout

- **WHEN** an authenticated client sends `POST /api/v1/auth/logout` with a valid `X-CSRF-Token`
- **THEN** the CSRF guard allows logout to clear the session cookie

#### Scenario: Valid CSRF token allows protected write

- **WHEN** an authenticated client sends a protected write request with a valid `X-CSRF-Token`
- **THEN** the CSRF guard allows the request to continue to the route handler

#### Scenario: Login may be explicitly exempt

- **WHEN** a client posts to `POST /api/v1/auth/login`
- **THEN** the route may be exempt from CSRF because there is no established session yet
- **AND** the exemption is explicitly documented in code or tests
- **AND** the exemption does not apply broadly to other protected writes

### Requirement: Unauthorized And Forbidden Error Envelope

Auth failures SHALL extend the existing `AppError` envelope behavior.

#### Scenario: Unauthorized response has stable shape

- **WHEN** an auth failure maps to unauthorized
- **THEN** the HTTP status is 401
- **AND** the response body contains `code`
- **AND** the response body contains `data`
- **AND** the response body contains `msg`
- **AND** the response body contains `error`
- **AND** `data` is null
- **AND** `error.code` is `UNAUTHORIZED`
- **AND** `error.request_id` matches the response `X-Request-ID` header

#### Scenario: Forbidden response has stable shape

- **WHEN** an auth failure maps to forbidden
- **THEN** the HTTP status is 403
- **AND** the response body contains `code`
- **AND** the response body contains `data`
- **AND** the response body contains `msg`
- **AND** the response body contains `error`
- **AND** `data` is null
- **AND** `error.code` is `FORBIDDEN`
- **AND** `error.request_id` matches the response `X-Request-ID` header

#### Scenario: Auth errors do not leak sensitive values

- **WHEN** an auth, capability, or CSRF error response is returned
- **THEN** the response does not contain administrator password, password hash, raw session, cookie value, signing secret, CSRF secret, private policy, database URL, token, or traceback

### Requirement: Actor Audit Context

API SHALL provide a safe actor/audit context helper for future high-risk handlers.

#### Scenario: Context contains actor and request metadata

- **WHEN** a protected route resolves actor/audit context
- **THEN** the context includes actor id
- **AND** the context includes actor type
- **AND** the context includes request id
- **AND** the context includes request method and path or equivalent request metadata
- **AND** the context can include the checked capability or capability snapshot

#### Scenario: Context excludes session secrets

- **WHEN** actor/audit context is passed to a downstream handler
- **THEN** the context does not include raw session, cookie value, signing secret, administrator password, password hash, CSRF secret, private policy, database URL, or full sensitive payload

### Requirement: Auth OpenAPI And Tests

Auth routes and guards SHALL be covered by runtime behavior tests and OpenAPI contract tests.

#### Scenario: Auth routes are visible in OpenAPI

- **WHEN** tests read development app `/openapi.json`
- **THEN** the schema contains `/api/v1/auth/login`
- **AND** the schema contains `/api/v1/auth/logout`
- **AND** the schema contains `/api/v1/me`
- **AND** each route has explicit tags
- **AND** successful responses use or reference `ApiResponse[...]`

#### Scenario: Auth tests cover enabled and disabled modes

- **WHEN** API tests run
- **THEN** they cover auth enabled protected-route rejection
- **AND** they cover valid session success
- **AND** they cover development auth disabled actor resolution
- **AND** they cover production rejection of disabled auth

#### Scenario: Auth tests cover sensitive data non-disclosure

- **WHEN** API tests exercise login, logout, me, unauthorized, forbidden, and CSRF errors
- **THEN** they assert responses do not include raw password, password hash, raw session, cookie value, signing secret, CSRF secret, private policy, or traceback

### Requirement: No Persistence Or Full User System In This Change

This change SHALL NOT claim or implement a complete user system.

#### Scenario: No user or session tables are required

- **WHEN** this change is implemented
- **THEN** it does not require a user table
- **AND** it does not require a session table
- **AND** it does not require an audit log table
- **AND** it does not require a database migration

#### Scenario: No multi-user or RBAC capability is claimed

- **WHEN** documentation or API responses describe the auth capability
- **THEN** they do not claim support for registration, multiple users, organizations, tenants, RBAC roles, OAuth, SSO, password reset, or email verification

