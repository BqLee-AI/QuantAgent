# Tasks: API Client 与全局错误治理

## 1. 核心类型定义

- [ ] 创建 `apps/web/src/shared/api/types.ts`
- [ ] 定义 `ApiResponse<T>` envelope 类型（code、`data: T | null`、msg、request_id?、trace_id?）
- [ ] 定义 `RequestConfig` 类型（signal、timeout、headers、params）
- [ ] 定义 `RefreshTokenContext` 类型（accessToken、method、url）
- [ ] 定义 `TokenRefreshResult` 类型（accessToken）
- [ ] 定义 `ApiClientConfig` 类型（baseURL、timeout、authEnabled、tokenProvider、refreshToken、onUnauthorized）
- [ ] 定义 `TokenProvider` 接口（getToken、setToken、clearToken）
- [ ] 定义 HTTP 方法类型和 `ApiMethod` 联合类型
- [ ] 添加注释说明后续可从 `@quantagent/contracts` 导入类型

## 2. Token 管理

- [ ] 创建 `apps/web/src/shared/api/token.ts`
- [ ] 实现 `createStorageTokenProvider(storage)` 工厂函数，支持 localStorage / sessionStorage
- [ ] 浏览器环境安全：window / Storage 不可用时 getToken 返回 null，setToken / clearToken 为 no-op
- [ ] 导出默认 `tokenProvider` 实例（使用 localStorage）

## 3. 错误定义与注册表

- [ ] 创建 `apps/web/src/shared/api/errors.ts`
- [ ] 实现 `ApiError` 类（继承 Error，含 code、msg、request_id、trace_id、status 字段）
- [ ] 定义 `ErrorBehavior` 联合类型（toast / modal / silent / redirect）
- [ ] 实现 `ErrorRegistry` Map（业务错误码 → { behavior, message? }）
- [ ] 添加 TODO 标注需与后端对齐 error code 类型

## 4. API Client 封装

- [ ] 创建 `apps/web/src/shared/api/client.ts`
- [ ] 实现 `createApiClient(config?)` 工厂函数，合并默认配置（baseURL `/api/v1`、timeout 10s、authEnabled false）
- [ ] 实现基础 `request<T>(method, url, body?, config?)` 方法
- [ ] 实现 Fetch 调用：构建 URL（baseURL + params）、设置 headers（Content-Type、条件 Auth）、AbortController timeout
- [ ] 实现响应解析：解析 JSON envelope，区分 HTTP 错误和业务错误
- [ ] 实现 code === 0 时解包返回 data，code !== 0 时抛 ApiError
- [ ] 实现 `requestEnvelope<T>()` 方法返回完整 envelope
- [ ] 实现 `get` / `post` / `put` / `patch` / `del` 便捷方法
- [ ] 预留 trace header TODO（X-Request-Id / X-Trace-Id 注入位置）
- [ ] 内部 pipeline：请求前处理（auth 注入、trace TODO）和响应后处理（envelope 解包、ApiError 转换、401 refresh），不暴露 interceptor API

## 5. 401 静默刷新

- [ ] 在 client.ts 中实现 401 拦截逻辑
- [ ] 使用共享 `refreshPromise` 避免并发刷新（401 refresh 并发去重）
- [ ] 调用 `refreshToken(context)` 时传入 `RefreshTokenContext`（accessToken、method、url）
- [ ] 刷新成功后更新 token 并重放原请求
- [ ] 刷新失败后清理 token、调用 onUnauthorized、抛 ApiError
- [ ] 未配置 refreshToken 时直接抛 ApiError

## 6. 导出与集成

- [ ] 创建 `apps/web/src/shared/api/index.ts`，统一导出所有公共 API
- [ ] 导出默认 `apiClient` 实例

## 7. Tests

- [ ] 添加 apiClient 成功解包测试：`code === 0` 时 `get<T>` 返回 `data`
- [ ] 添加完整 envelope 测试：`requestEnvelope<T>` 返回 `{ code, data, msg }`
- [ ] 添加业务错误测试：`code !== 0` 时抛出 `ApiError`
- [ ] 添加 HTTP 错误测试：非 2xx 响应抛出带 status 的 `ApiError`
- [ ] 添加 auth 开关测试：默认不注入 `Authorization`，开启后注入 `Bearer <token>`
- [ ] 添加 timeout / AbortController 测试
- [ ] 添加 401 单请求静默刷新测试
- [ ] 添加 401 并发刷新去重测试：多个 401 只调用一次 `refreshToken`
- [ ] 添加 refresh 失败测试：清理 token，调用 `onUnauthorized`，抛出 `ApiError`
- [ ] 添加 error registry 测试：业务码映射到默认 UI 行为

## 8. Verification

- [ ] 确认 `bun run lint` 通过
- [ ] 确认 `bun run build --filter=web` 通过
- [ ] 确认相关测试命令通过
- [ ] 确认 `openspec validate api-client-error-governance --strict` 通过
