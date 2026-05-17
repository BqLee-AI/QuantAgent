# API Client 与全局错误治理 Specification

## ADDED Requirements

### Requirement: Shared API Module

`apps/web/src/shared/api/` SHALL 提供统一的 API client 模块。

#### Scenario: API module exports are available

- **WHEN** 开发者导入 `@/shared/api`
- **THEN** 可以获得 `apiClient`、`createApiClient`、`ApiError`、`ErrorRegistry` 和相关类型

### Requirement: Strongly Typed Envelope Handling

前端 SHALL 支持后端 `code/data/msg` envelope 协议。

#### Scenario: Successful response auto-unpacks business data

- **WHEN** 调用 `apiClient.get<User>("/me")`
- **AND** 响应体为 `{ code: 0, data: { id: 1 }, msg: "ok" }`
- **THEN** 返回值为 `User`

#### Scenario: Full envelope remains available

- **WHEN** 调用 `apiClient.requestEnvelope<User>("/me")`
- **AND** 响应体为 `{ code: 0, data: { id: 1 }, msg: "ok" }`
- **THEN** 返回完整 envelope

#### Scenario: Business failure becomes ApiError

- **WHEN** 响应体为 `{ code: 40001, data: null, msg: "参数错误" }`
- **THEN** client 抛出 `ApiError`
- **AND** 保留 `code`、`msg`、`request_id`、`trace_id`

### Requirement: Authentication Injection

API client SHALL 支持可开关的 Bearer token 注入。

#### Scenario: Authorization header is injected when auth is enabled

- **WHEN** `authEnabled` 为 `true`
- **AND** token provider 或本地存储中存在 token
- **THEN** 请求头包含 `Authorization: Bearer <token>`

#### Scenario: Authorization stays disabled by default

- **WHEN** 使用默认 `apiClient`
- **THEN** 不注入 `Authorization` header

### Requirement: 401 Silent Refresh

API client SHALL 集中处理 401 场景。

#### Scenario: Refresh succeeds and request is replayed

- **WHEN** 原始请求返回 401
- **AND** 已配置 `refreshAccessToken`
- **AND** refresh 成功
- **THEN** client 重放原始请求并返回结果

#### Scenario: Concurrent 401 shares one refresh promise

- **WHEN** 多个请求同时返回 401
- **AND** 已配置 `refreshAccessToken`
- **THEN** 仅触发一次 refresh 调用
- **AND** 各请求等待同一 refresh promise

#### Scenario: Refresh failure escalates unauthorized

- **WHEN** refresh 失败
- **THEN** client 调用 `onUnauthorized`
- **AND** 抛出 `ApiError`

### Requirement: Error Governance

前端 SHALL 统一封装 API 失败语义。

#### Scenario: ApiError preserves metadata

- **WHEN** 抛出 `ApiError`
- **THEN** 至少包含 `code`、`msg`、`status`
- **AND** 如可用则包含 `requestId` 和 `traceId`

#### Scenario: Error registry maps business codes to UI behavior

- **WHEN** 查询 `ErrorRegistry`
- **THEN** 可获得 `toast | modal | silent | redirect` 等默认 UI 行为
- **AND** registry 本身不直接渲染 UI

#### Scenario: Global error hook can observe failures

- **WHEN** client 产生 `ApiError`
- **THEN** 若配置了 `onError`，该 hook 会收到统一错误对象

### Requirement: Lifecycle And Request Deduplication

API client SHALL 支持组件生命周期安全与基础请求去重。

#### Scenario: AbortSignal is forwarded

- **WHEN** 调用方传入 `signal`
- **THEN** client 将该 `signal` 透传给底层请求

#### Scenario: Duplicate GET requests reuse inflight promise

- **WHEN** 相同 GET 请求在前一个请求完成前再次发起
- **THEN** client 复用同一个 inflight promise

### Requirement: Trace Header Extension Point

请求链路追踪 SHALL 保留实现扩展点。

#### Scenario: Trace injection todo is preserved

- **WHEN** 开发者检查 request interceptor
- **THEN** 能看到 `X-Request-Id` / `X-Trace-Id` 的 TODO 注释
- **AND** 当前不会生成真实 trace id

### Requirement: Verification

本 change 完成后 SHALL 通过前端单元测试、lint 和构建验证。

#### Scenario: Required commands pass

- **WHEN** 运行 `bun --cwd apps/web run test:unit`
- **THEN** API client 相关测试通过

- **WHEN** 运行 `bun run lint`
- **THEN** 静态检查通过

- **WHEN** 运行 `bun run build --filter=web`
- **THEN** 前端构建通过
