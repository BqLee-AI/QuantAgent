# Tasks: API Client 与全局错误治理

## 1. Dependencies

- [ ] 在 `apps/web` 添加 `axios` 依赖
- [ ] 确认 lockfile 更新正确

## 2. Core Types

- [ ] 创建 `apps/web/src/shared/api/types.ts`
- [ ] 定义 `ApiResponse<T>`，其中 `data` 支持 `T | null`
- [ ] 定义 `RequestConfig`，兼容 Axios request config 的必要字段
- [ ] 定义 `ApiClientConfig`：baseURL、timeout、withCredentials、headers、onUnauthorized、recoverUnauthorized
- [ ] 定义 `ApiMethod` 联合类型
- [ ] 预留 `packages/contracts` 类型入口注释

## 3. Error Handling

- [ ] 创建 `apps/web/src/shared/api/errors.ts`
- [ ] 实现 `ApiError` 类（继承 Error，含 code、msg、request_id、trace_id、status）
- [ ] 实现 AxiosError → ApiError 转换函数
- [ ] 定义 `ErrorBehavior` 联合类型（toast / modal / silent / redirect）
- [ ] 实现 `ErrorRegistry` Map（业务错误码 → { behavior, message? }），registry 不直接弹 UI
- [ ] 添加 TODO 标注需与后端对齐 error code 类型

## 4. Axios Client

- [ ] 创建 `apps/web/src/shared/api/client.ts`
- [ ] 创建 Axios instance，默认 `baseURL=/api/v1`、`timeout=10000`、`withCredentials=true`
- [ ] 实现 request interceptor
- [ ] 在 request interceptor 中预留 trace header TODO
- [ ] 确认不注入 Authorization Bearer token
- [ ] 允许透传业务 headers
- [ ] 实现 response interceptor envelope 解包和 ApiError 转换
- [ ] 实现 `get` / `post` / `put` / `patch` / `del` 便捷方法
- [ ] 实现 `requestEnvelope<T>()` 返回完整 envelope

## 5. 401 Cookie Session Handling

- [ ] 在 response interceptor 中捕获 401 Axios error
- [ ] 创建 ApiError，status 为 401
- [ ] 调用 `onUnauthorized(error)` 回调
- [ ] 支持可选 `recoverUnauthorized`
- [ ] 使用共享 `recoverPromise` 避免并发恢复
- [ ] recover 成功后重放原请求
- [ ] recover 失败后不重放，抛 ApiError
- [ ] 不实现 localStorage/sessionStorage token refresh

## 6. Exports

- [ ] 创建 `apps/web/src/shared/api/index.ts`
- [ ] 导出 `apiClient`、`createApiClient`、`ApiError`、`ErrorRegistry` 和类型

## 7. Tests

- [ ] 测试 Axios instance 默认 baseURL、timeout、withCredentials
- [ ] 测试不注入 Authorization header
- [ ] 测试 trace TODO 位置存在
- [ ] 测试自定义 header 透传
- [ ] 测试 `code === 0` 自动返回 `envelope.data`
- [ ] 测试 `requestEnvelope` 返回完整 envelope
- [ ] 测试 `code !== 0` 抛 ApiError
- [ ] 测试 HTTP / Axios error 转 ApiError
- [ ] 测试 401 调用 onUnauthorized
- [ ] 测试 `recoverUnauthorized` 成功后重放请求
- [ ] 测试并发 401 只调用一次 `recoverUnauthorized`
- [ ] 测试 `recoverUnauthorized` 失败后抛 ApiError
- [ ] 测试 error registry 业务码映射到默认 UI 行为

## 8. Verification

- [ ] `bun run lint` 通过
- [ ] `bun run build --filter=web` 通过
- [ ] 相关测试命令通过
- [ ] `openspec validate api-client-error-governance --strict` 通过
