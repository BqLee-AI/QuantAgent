# API Cookie Session Auth 规格

## MODIFIED Requirements

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
