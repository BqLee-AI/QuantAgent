## MODIFIED Requirements

### Requirement: Authentication Injection

API client SHALL 以 Cookie Session 为主鉴权路径，并集中处理前端 auth bootstrap 相关 header 注入。

#### Scenario: Cookie-session requests keep credentials enabled

- **WHEN** 前端通过默认 shared API client 发起请求
- **THEN** 请求保留 `withCredentials=true`
- **AND** 浏览器可自动携带 HttpOnly session cookie

#### Scenario: CSRF header is injected from auth bootstrap state

- **WHEN** 当前前端 auth bootstrap 状态中存在 `csrf_token`
- **AND** 调用受保护写请求或 logout
- **THEN** shared API client 统一注入 `X-CSRF-Token`
- **AND** 页面组件不需要手写该 header

#### Scenario: Bearer token injection is not the primary auth path

- **WHEN** 实现本地单用户 Cookie Session 登录接入
- **THEN** shared API client 不要求从本地存储读取 Bearer token 才能完成本轮登录态管理
- **AND** 登录页、`GET /api/v1/me` bootstrap、`POST /api/v1/auth/logout` 和受保护写请求都不得以 Bearer token 作为成立前提

#### Scenario: Compatibility extension does not redefine the main auth path

- **WHEN** 实现仍临时保留 Bearer token 或 refresh 相关扩展点
- **THEN** 这些扩展点只能被视为兼容保留
- **AND** 不得把本轮主鉴权路径从 Cookie Session + `X-CSRF-Token` 改回 token 驱动

### Requirement: 401 Silent Refresh

API client SHALL 集中处理 401 场景，但在本地单用户 Cookie Session 登录接入中，401 的默认收口是未登录态恢复，而不是前端 refresh token 流程。

#### Scenario: Unauthorized error calls the centralized unauthorized handler

- **WHEN** 受保护请求返回 401
- **THEN** shared API client 调用统一 `onUnauthorized`
- **AND** 调用方可以通过该入口清理前端 auth bootstrap 状态

#### Scenario: Cookie-session login flow does not require refresh token replay

- **WHEN** 本轮前端消费 `/auth/login`、`/auth/logout` 与 `/me`
- **THEN** shared API client 不依赖 refresh token endpoint、cookie refresh 或请求重放才能完成既定登录流程

#### Scenario: Unauthorized handling remains centralized

- **WHEN** 页面或 feature 模块调用 shared API client
- **THEN** 401 行为通过统一入口处理
- **AND** 页面组件不各自维护跳转登录页和状态清理逻辑

#### Scenario: Sensitive auth failures do not leak values

- **WHEN** shared API client 处理 401、403 或 CSRF 相关失败
- **THEN** 前端错误对象、共享状态和日志中不暴露 session cookie、cookie value、password、password hash、signing secret、真实 token 或私有策略原文
