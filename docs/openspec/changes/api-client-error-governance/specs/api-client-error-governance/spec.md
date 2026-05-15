# API Client 与全局错误治理 Specification

## ADDED Requirements

### Requirement: Core Types

`apps/web/src/shared/api/types.ts` SHALL 定义 API Client 所需的核心类型。

#### Scenario: Envelope type defined

- **WHEN** 开发者导入 `ApiResponse`
- **THEN** 类型包含 `code: number`、`data: T`、`msg: string`
- **AND** 可选字段包含 `request_id?: string`、`trace_id?: string`

#### Scenario: Request config type defined

- **WHEN** 开发者导入 `RequestConfig`
- **THEN** 类型支持 `signal?: AbortSignal`、`timeout?: number`、`headers?: Record<string, string>`
- **AND** 支持 `params?: Record<string, string | number | boolean>`（URL query 参数）

#### Scenario: Client config type defined

- **WHEN** 开发者导入 `ApiClientConfig`
- **THEN** 类型包含 `baseURL: string`（默认 `/api/v1`）、`timeout: number`（默认 10000ms）
- **AND** 包含 `authEnabled: boolean`（默认 `false`）
- **AND** 包含 `tokenProvider?: TokenProvider`
- **AND** 包含 `refreshToken?: (token: string) => Promise<{ accessToken: string }>`
- **AND** 包含 `onUnauthorized?: () => void`（刷新失败回调）

### Requirement: Token Management

`apps/web/src/shared/api/token.ts` SHALL 封装 token 存取与 provider 抽象。

#### Scenario: Token provider abstraction

- **WHEN** 开发者使用默认 token provider
- **THEN** 默认从 `localStorage` 读写 access token
- **AND** 可通过配置切换为 `sessionStorage`

#### Scenario: Token auth switch

- **WHEN** `ApiClientConfig.authEnabled` 为 `false`（默认）
- **THEN** 请求不注入 `Authorization` header
- **WHEN** `authEnabled` 为 `true`
- **THEN** 请求自动注入 `Authorization: Bearer <token>`

### Requirement: API Client

`apps/web/src/shared/api/client.ts` SHALL 基于 Fetch 封装强类型 HTTP 客户端。

#### Scenario: GET request with auto-unpack

- **WHEN** 开发者调用 `apiClient.get<User>('/me')`
- **AND** 后端返回 `{ code: 0, data: { id: 1, name: "..." }, msg: "ok" }`
- **THEN** 返回值类型为 `Promise<User>`，运行时值为 `{ id: 1, name: "..." }`

#### Scenario: GET request with envelope

- **WHEN** 开发者调用 `apiClient.requestEnvelope<User>('/me')`
- **AND** 后端返回 `{ code: 0, data: { id: 1 }, msg: "ok" }`
- **THEN** 返回值类型为 `Promise<ApiResponse<User>>`，包含完整 `{ code, data, msg }`

#### Scenario: POST request

- **WHEN** 开发者调用 `apiClient.post<CreateBody, CreateResult>('/items', body)`
- **THEN** 请求方法为 POST，body JSON 序列化后发送
- **AND** 成功时返回 `CreateResult`

#### Scenario: Business error throws ApiError

- **WHEN** 后端返回 `{ code: 40001, data: null, msg: "参数错误" }`
- **THEN** 抛出 `ApiError`，`code` 为 40001，`msg` 为 "参数错误"

#### Scenario: HTTP error throws ApiError

- **WHEN** HTTP 响应状态码为 500
- **THEN** 抛出 `ApiError`，`status` 为 500
- **AND** 尝试解析响应体中的 `code`/`msg`，解析失败则使用默认消息

#### Scenario: Timeout

- **WHEN** 请求超过配置的 timeout（默认 10s）
- **THEN** 请求被 AbortController 取消
- **AND** 抛出 `ApiError`，标记为超时错误

#### Scenario: Request cancellation

- **WHEN** 开发者传入 `signal: AbortSignal`
- **THEN** signal 触发时请求被取消

#### Scenario: Trace headers reserved

- **WHEN** 开发者检查 client.ts 代码
- **THEN** 存在 TODO 注释标注 `X-Request-Id` / `X-Trace-Id` 注入位置
- **AND** 不存在实际的 trace ID 生成逻辑

### Requirement: 401 Silent Refresh

apiClient SHALL 在收到 401 响应时自动尝试 Token 刷新。

#### Scenario: Single 401 triggers refresh

- **WHEN** 请求返回 401 且 `refreshToken` 函数已配置
- **THEN** 使用当前 token 调用 `refreshToken` 获取新 access token
- **AND** 刷新成功后使用新 token 重放原请求
- **AND** 返回重放请求的结果

#### Scenario: Concurrent 401 shares refresh

- **WHEN** 多个请求同时收到 401
- **THEN** 仅触发一次 `refreshToken` 调用
- **AND** 所有并发请求等待同一 refresh promise
- **AND** 刷新成功后所有请求均使用新 token 重放

#### Scenario: Refresh failure

- **WHEN** `refreshToken` 调用失败
- **THEN** 清理已存储的 access token
- **AND** 调用 `onUnauthorized` 回调（如已配置）
- **AND** 抛出 `ApiError`

#### Scenario: No refresh function configured

- **WHEN** 请求返回 401 且未配置 `refreshToken`
- **THEN** 直接抛出 `ApiError`，不尝试刷新

### Requirement: ApiError

`apps/web/src/shared/api/errors.ts` SHALL 定义统一的错误类和错误注册表。

#### Scenario: ApiError fields

- **WHEN** 抛出 ApiError
- **THEN** 包含 `code: number`（业务错误码或 HTTP 状态码）
- **AND** 包含 `msg: string`
- **AND** 包含 `request_id?: string`
- **AND** 包含 `trace_id?: string`
- **AND** 包含 `status?: number`（HTTP 状态码）
- **AND** 继承自 `Error`

#### Scenario: Error registry

- **WHEN** 开发者检查 `errors.ts`
- **THEN** 存在 `ErrorRegistry`，将业务错误码映射到 UI 行为类型
- **AND** 行为类型包含 `toast | modal | silent | redirect` 联合类型
- **AND** 存在 TODO 标注需与后端对齐实际 error code 类型

### Requirement: Contracts Package Entry

`packages/contracts` SHALL 预留类型入口。

#### Scenario: Contracts placeholder

- **WHEN** 开发者检查 `packages/contracts`
- **THEN** 目录存在（当前仅 `.gitkeep`）
- **AND** `apps/web/src/shared/api/types.ts` 包含注释说明后续可从 `@quantagent/contracts` 导入类型

### Requirement: Build Verification

所有改动后 `bun run build` SHALL 通过。

#### Scenario: Build passes

- **WHEN** 运行 `bun run build --filter=web`
- **THEN** tsc 和 vite build 均成功，无错误
