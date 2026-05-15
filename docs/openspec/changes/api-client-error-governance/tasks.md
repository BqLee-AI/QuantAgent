# Tasks: API Client 与全局错误治理

## 1. 核心类型定义

- [ ] 创建 `apps/web/src/shared/api/types.ts`
- [ ] 定义 `ApiResponse<T>` envelope 类型（code、data、msg、request_id?、trace_id?）
- [ ] 定义 `RequestConfig` 类型（signal、timeout、headers、params）
- [ ] 定义 `ApiClientConfig` 类型（baseURL、timeout、authEnabled、tokenProvider、refreshToken、onUnauthorized）
- [ ] 定义 `TokenProvider` 接口（getToken、setToken、clearToken）
- [ ] 定义 HTTP 方法类型和 `ApiMethod` 联合类型

## 2. Token 管理

- [ ] 创建 `apps/web/src/shared/api/token.ts`
- [ ] 实现 `createStorageTokenProvider(storage)` 工厂函数，支持 localStorage / sessionStorage
- [ ] 导出默认 `tokenProvider` 实例（使用 localStorage）

## 3. 错误定义与注册表

- [ ] 创建 `apps/web/src/shared/api/errors.ts`
- [ ] 实现 `ApiError` 类（继承 Error，含 code、msg、request_id、trace_id、status 字段）
- [ ] 定义 `ErrorBehavior` 联合类型（toast / modal / silent / redirect）
- [ ] 实现 `ErrorRegistry` Map（业务错误码 → { behavior, message? }）
- [ ] 添加 TODO 标注需与后端对齐 error code 类型

## 4. API Client 封装

- [ ] 创建 `apps/web/src/shared/api/client.ts`
- [ ] 实现 `createApiClient(config?)` 工厂函数，合并默认配置
- [ ] 实现基础 `request<T>(method, url, body?, config?)` 方法
- [ ] 实现 Fetch 调用：构建 URL（baseURL + params）、设置 headers（Content-Type、Auth）、AbortController timeout
- [ ] 实现响应解析：解析 JSON envelope，区分 HTTP 错误和业务错误
- [ ] 实现 code === 0 时解包返回 data，code !== 0 时抛 ApiError
- [ ] 实现 `requestEnvelope<T>()` 方法返回完整 envelope
- [ ] 实现 `get` / `post` / `put` / `patch` / `del` 便捷方法
- [ ] 预留 trace header TODO（X-Request-Id / X-Trace-Id 注入位置）

## 5. 401 静默刷新

- [ ] 在 client.ts 中实现 401 拦截逻辑
- [ ] 使用共享 `refreshPromise` 避免并发刷新
- [ ] 刷新成功后更新 token 并重放原请求
- [ ] 刷新失败后清理 token、调用 onUnauthorized、抛 ApiError
- [ ] 未配置 refreshToken 时直接抛 ApiError

## 6. 导出与集成

- [ ] 创建 `apps/web/src/shared/api/index.ts`，统一导出所有公共 API
- [ ] 导出默认 `apiClient` 实例
- [ ] 在 `types.ts` 中添加注释说明后续可从 `@quantagent/contracts` 导入类型

## 7. Verification

- [ ] 确认 `bun run lint` 通过
- [ ] 确认 `bun run build --filter=web` 通过
- [ ] 确认 `openspec validate api-client-error-governance --strict` 通过
