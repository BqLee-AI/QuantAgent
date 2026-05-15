# API Client 与全局错误治理 Specification

## ADDED Requirements

### Requirement: Core Types

`apps/web/src/shared/api/types.ts` SHALL 定义 API Client 所需的核心类型。

#### Scenario: Envelope type defined

- **WHEN** 开发者导入 `ApiResponse`
- **THEN** 类型包含 `code: number`、`data: T | null`、`msg: string`
- **AND** 可选字段包含 `request_id?: string`、`trace_id?: string`
- **NOTE** 错误响应常见 `{ code, data: null, msg }`，`data` 必须支持 null

#### Scenario: Request config type defined

- **WHEN** 开发者导入 `RequestConfig`
- **THEN** 类型兼容 Axios request config 的必要字段（signal、timeout、headers、params）
- **AND** 支持 `params?: Record<string, string | number | boolean>`（URL query 参数）

#### Scenario: Client config type defined

- **WHEN** 开发者导入 `ApiClientConfig`
- **THEN** 类型包含 `baseURL?: string`（默认 `/api/v1`）、`timeout?: number`（默认 10000ms）
- **AND** 包含 `withCredentials?: boolean`（默认 `true`）
- **AND** 包含 `headers?: Record<string, string>`（默认 headers）
- **AND** 包含 `onUnauthorized?: (error: ApiError) => void`（401 回调）
- **AND** 包含 `recoverUnauthorized?: () => Promise<void>`（可选会话恢复函数）
- **AND** 不包含 `authEnabled`、`tokenProvider`、`refreshToken` 字段

### Requirement: Axios Client Instance

apiClient SHALL 使用 Axios 作为 HTTP 传输层。

#### Scenario: Default Axios config

- **WHEN** 使用 `createApiClient()` 不传参
- **THEN** 创建的 Axios instance 的 `baseURL` 为 `/api/v1`
- **AND** `timeout` 为 10000ms
- **AND** `withCredentials` 为 `true`

#### Scenario: Custom Axios config

- **WHEN** 开发者传入自定义 config
- **THEN** 自定义值覆盖默认值
- **AND** 未指定的字段保持默认值

#### Scenario: No raw fetch

- **WHEN** 开发者检查 `client.ts`
- **THEN** 不存在直接使用 `fetch()` 或 `globalThis.fetch()` 的调用
- **AND** 所有 HTTP 请求通过 Axios instance 发出

### Requirement: Request Interceptors

apiClient SHALL 在 Axios instance 上注册 request interceptor。

#### Scenario: No Authorization header injection

- **WHEN** 请求发送
- **THEN** 不注入 `Authorization: Bearer <token>` header
- **AND** 不读取 localStorage / sessionStorage 中的 token

#### Scenario: Trace header TODO

- **WHEN** 开发者检查 request interceptor 代码
- **THEN** 存在 TODO 注释标注 `X-Request-Id` / `X-Trace-Id` 注入位置
- **AND** 不存在实际的 trace ID 生成逻辑

#### Scenario: Custom headers passthrough

- **WHEN** 开发者通过 config 传入自定义 headers
- **THEN** headers 被合并到请求中

### Requirement: Response Interceptors

apiClient SHALL 在 Axios instance 上注册 response interceptor，处理 envelope 解包和错误转换。

**关键区分**：Axios 的 `response.data` 是 HTTP 响应体，即业务 envelope `{ code, data, msg }`。envelope 的 `data` 字段才是业务数据。`get<T>()` 默认返回 `envelope.data`，`requestEnvelope<T>()` 返回完整 `response.data`。

#### Scenario: GET request with auto-unpack

- **WHEN** 开发者调用 `apiClient.get<User>('/me')`
- **AND** Axios `response.data` 为 `{ code: 0, data: { id: 1, name: "..." }, msg: "ok" }`
- **THEN** 返回值类型为 `Promise<User>`，运行时值为 `{ id: 1, name: "..." }`

#### Scenario: GET request with envelope

- **WHEN** 开发者调用 `apiClient.requestEnvelope<User>('/me')`
- **AND** Axios `response.data` 为 `{ code: 0, data: { id: 1 }, msg: "ok" }`
- **THEN** 返回值类型为 `Promise<ApiResponse<User>>`，包含完整 `{ code, data, msg }`

#### Scenario: POST request

- **WHEN** 开发者调用 `apiClient.post<CreateBody, CreateResult>('/items', body)`
- **THEN** 请求方法为 POST，body JSON 序列化后发送
- **AND** 成功时返回 `CreateResult`

#### Scenario: Business error throws ApiError

- **WHEN** Axios `response.data` 为 `{ code: 40001, data: null, msg: "参数错误" }`（HTTP 200）
- **THEN** 抛出 `ApiError`，`code` 为 40001，`msg` 为 "参数错误"

#### Scenario: HTTP error throws ApiError

- **WHEN** Axios 收到 HTTP 500 响应
- **THEN** 抛出 `ApiError`，`status` 为 500
- **AND** 尝试解析 `error.response.data` 中的 `code`/`msg`，解析失败则使用默认消息

#### Scenario: Network error throws ApiError

- **WHEN** Axios 抛出网络错误（无响应）
- **THEN** 转换为 `ApiError`，包含合理的默认 `code` 和 `msg`

### Requirement: 401 Cookie Session Handling

apiClient SHALL 集中处理 401 会话过期，不实现 Bearer token refresh。

#### Scenario: 401 triggers onUnauthorized

- **WHEN** 请求返回 HTTP 401
- **THEN** 创建 `ApiError`，`status` 为 401
- **AND** 调用 `onUnauthorized(error)` 回调（如已配置）
- **AND** 抛出该 `ApiError`

#### Scenario: 401 with recoverUnauthorized

- **WHEN** 请求返回 HTTP 401 且配置了 `recoverUnauthorized`
- **THEN** 执行 `recoverUnauthorized()`
- **AND** 恢复成功后使用新 Cookie 重放原请求
- **AND** 返回重放请求的结果

#### Scenario: Concurrent 401 shares recover

- **WHEN** 多个请求同时收到 401 且配置了 `recoverUnauthorized`
- **THEN** 仅执行一次 `recoverUnauthorized` 调用
- **AND** 所有并发请求等待同一 recover promise
- **AND** 恢复成功后所有请求均重放

#### Scenario: Recover failure

- **WHEN** `recoverUnauthorized` 调用失败
- **THEN** 不重放请求
- **AND** 调用 `onUnauthorized` 回调（如已配置）
- **AND** 抛出 `ApiError`

#### Scenario: No recoverUnauthorized configured

- **WHEN** 请求返回 401 且未配置 `recoverUnauthorized`
- **THEN** 直接调用 `onUnauthorized` 并抛出 `ApiError`，不尝试恢复

#### Scenario: No token storage access

- **WHEN** 开发者检查 401 处理代码
- **THEN** 不存在 localStorage / sessionStorage 读写 token 的逻辑
- **AND** 不存在 Authorization header 注入逻辑

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

#### Scenario: Axios error to ApiError conversion

- **WHEN** Axios 抛出错误
- **THEN** 存在转换函数将 AxiosError 转为 ApiError
- **AND** 保留原始 Axios error 作为 cause

#### Scenario: Error registry

- **WHEN** 开发者检查 `errors.ts`
- **THEN** 存在 `ErrorRegistry`，将业务错误码映射到 UI 行为类型
- **AND** 行为类型包含 `toast | modal | silent | redirect` 联合类型
- **AND** registry 不直接弹 UI，只返回默认行为描述
- **AND** UI 消费由上层接入
- **AND** 存在 TODO 标注需与后端对齐实际 error code 类型

### Requirement: Contracts Package Entry

`packages/contracts` SHALL 预留类型入口。

#### Scenario: Contracts placeholder

- **WHEN** 开发者检查 `packages/contracts`
- **THEN** 目录存在（当前仅 `.gitkeep`）
- **AND** `apps/web/src/shared/api/types.ts` 包含注释说明后续可从 `@quantagent/contracts` 导入类型

### Requirement: API Client Tests

apiClient 及其依赖模块 SHALL 有自动化测试覆盖。

#### Scenario: Axios instance config test

- **WHEN** 创建默认 apiClient
- **THEN** Axios instance 的 baseURL、timeout、withCredentials 符合默认值

#### Scenario: No Authorization injection test

- **WHEN** 发送请求
- **THEN** 请求 headers 中不包含 `Authorization`

#### Scenario: Trace TODO exists test

- **WHEN** 检查 request interceptor 代码
- **THEN** 存在 trace header TODO 注释

#### Scenario: Custom header passthrough test

- **WHEN** 传入自定义 headers
- **THEN** 请求包含该 headers

#### Scenario: Success unpack test

- **WHEN** Axios mock `response.data` 为 `{ code: 0, data: { ... }, msg: "ok" }`
- **THEN** `apiClient.get<T>(url)` 返回 `envelope.data` 部分

#### Scenario: Envelope return test

- **WHEN** 使用 `requestEnvelope<T>(url)`
- **THEN** 返回完整 `{ code, data, msg }`

#### Scenario: Business error test

- **WHEN** `response.data` 为 `{ code: 40001, data: null, msg: "参数错误" }`
- **THEN** 抛出 `ApiError` 且 `code === 40001`

#### Scenario: HTTP error test

- **WHEN** Axios 返回 HTTP 500
- **THEN** 抛出 `ApiError` 且 `status === 500`

#### Scenario: Network error test

- **WHEN** Axios 抛出网络错误
- **THEN** 转换为 `ApiError`

#### Scenario: 401 calls onUnauthorized test

- **WHEN** 收到 401 且未配置 recoverUnauthorized
- **THEN** 调用 `onUnauthorized` 并抛出 `ApiError`

#### Scenario: Recover success replays test

- **WHEN** 收到 401 且 `recoverUnauthorized` 成功
- **THEN** 使用新 Cookie 重放原请求并返回结果

#### Scenario: Concurrent 401 one recover test

- **WHEN** 多个请求同时收到 401
- **THEN** `recoverUnauthorized` 仅被调用一次

#### Scenario: Recover failure test

- **WHEN** `recoverUnauthorized` 调用失败
- **THEN** 不重放请求，调用 `onUnauthorized`，抛出 `ApiError`

#### Scenario: Error registry maps codes test

- **WHEN** 查询已知业务错误码
- **THEN** registry 返回对应的 `{ behavior, message? }`

### Requirement: Build Verification

所有改动后 `bun run build` SHALL 通过。

#### Scenario: Build passes

- **WHEN** 运行 `bun run build --filter=web`
- **THEN** tsc 和 vite build 均成功，无错误
