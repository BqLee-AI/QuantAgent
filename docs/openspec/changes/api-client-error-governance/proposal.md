# Change: API Client 与全局错误治理

## Why

前端数据层缺乏统一的 HTTP 客户端封装，当前各页面/组件直接使用裸 fetch 或 TanStack Query，存在以下问题：
- 无统一 baseURL、timeout、请求/响应拦截，请求配置分散。
- 后端响应 envelope（`{ code, data, msg }`）的解包逻辑在各处重复实现。
- 401 后缺少统一会话过期处理，无法自动恢复或引导用户重新认证。
- 业务错误码无集中注册表，错误处理行为不一致。

本 change 封装一个强类型 `apiClient`，基于 Axios（利用 instance 与 interceptors），集成 Cookie 会话认证、响应 envelope 解包、401 会话恢复和全局错误治理，为 TanStack Query 等上层消费者提供可靠的数据层基础。

## Design Decisions

- **Axios 作为 HTTP 传输层**：利用 Axios instance 与 interceptors 实现统一请求/响应治理，不使用裸 fetch wrapper。
- **Cookie 会话认证**：前端不持有 access token / refresh token，不注入 Bearer token。请求通过 Cookie 携带会话，Axios 开启 `withCredentials`。
- **401 会话恢复**：定义为 cookie session 过期治理——默认抛 `ApiError` 并触发 `onUnauthorized`；如配置 `recoverUnauthorized`，可尝试一次会话恢复并重放请求。不实现双 token refresh。
- **Trace header**：当前只保留 TODO 注入点，不生成真实 request id / trace id。
- **ErrorRegistry**：只描述默认 UI 行为（toast/modal/silent/redirect），不直接依赖 UI 组件。

## What Changes

- **`apps/web/src/shared/api/types.ts`**：定义 `ApiResponse<T>` envelope、`RequestConfig`、`ApiClientConfig` 等核心类型。
- **`apps/web/src/shared/api/errors.ts`**：定义 `ApiError` 类（含 code、msg、request_id、trace_id、status），Axios error → ApiError 转换函数，以及业务错误码注册表。
- **`apps/web/src/shared/api/client.ts`**：基于 Axios 的 `apiClient` 封装，包含：
  - 创建 Axios instance，baseURL 默认 `/api/v1`，timeout 10s，`withCredentials: true`
  - request interceptor：预留 trace header TODO，不注入 Authorization Bearer token，透传业务 headers
  - response interceptor：解析 `response.data` 为业务 envelope，`code === 0` 时解包返回 `envelope.data`，`code !== 0` 时抛 `ApiError`
  - `get<T>` / `post<TBody, TResponse>` / `put` / `patch` / `del` 便捷方法
  - `requestEnvelope<T>()` 方法返回完整 `{ code, data, msg }` envelope
  - 401 会话恢复（可选 `recoverUnauthorized`，共享 recover promise 避免并发）
- **`apps/web/src/shared/api/index.ts`**：统一导出。
- **`packages/contracts`**：预留类型入口（`.gitkeep` 已存在），不实现生成流程。

## Out Of Scope

- 不实现 Bearer Token / 双 token refresh。
- 不把 token 存 localStorage / sessionStorage，不注入 Authorization header。
- 不实现 UI 层 toast/modal 弹窗（error registry 只定义行为映射，UI 消费留给后续 issue）。
- 不实现跨业务的全局请求缓存/去重；TanStack Query 负责 query 层重复请求合并。apiClient 仅实现 401 recover 并发去重。非 Query 场景的通用请求去重后续单独设计。
- Trace header 只预留 TODO，不实现真实 trace ID 生成逻辑。
- 后端 error code 类型定义待与后端对齐，本 change 只定义前端侧框架。
- 本 change 仅覆盖前端数据层，不涉及 UI 视觉系统或设计 token。

## Success Criteria

- `apiClient.get<User>('/me')` 成功时返回 `User` 类型。
- `apiClient.requestEnvelope<User>('/me')` 返回完整 `{ code, data, msg }` envelope。
- 后端返回非 0 code 时抛出 `ApiError`，包含 code、msg、request_id、trace_id。
- 401 响应触发 `onUnauthorized`；配置 `recoverUnauthorized` 时尝试恢复并重放，并发请求共享同一 recover promise。
- Axios instance 默认 `withCredentials: true`，请求携带 Cookie。
- `bun run build --filter=web` 通过。

## Testing Strategy

- Axios instance config 测试：baseURL、timeout、withCredentials。
- Request interceptor 测试：不注入 Authorization、trace TODO 位置存在、自定义 header 透传。
- Response interceptor 测试：`response.data` envelope 解包返回 `envelope.data`、`requestEnvelope` 返回完整 envelope、`code !== 0` 抛 ApiError、Axios network error 转 ApiError。
- 401 handling 测试：401 调用 onUnauthorized、配置 recoverUnauthorized 时执行恢复并重放、并发 401 只调用一次 recoverUnauthorized、recover 失败抛 ApiError。
- 确认没有 localStorage/sessionStorage token provider 逻辑。
- ErrorRegistry 测试：业务码映射到默认 UI 行为。
- 类型验证通过 `bun run build --filter=web`。
- 若仓库尚未配置测试框架，本 change 应补充最小测试运行能力（vitest 或等价工具）。

## Open Questions

- **后端 error code 类型**：需与后端确认业务错误码的完整枚举（如风控错误、限流错误等），当前 registry 仅定义框架和占位。
- **Cookie session recover 接口**：如后端提供 session refresh endpoint，需确认路径和请求/响应格式。
- **Trace header 生成策略**：`X-Request-Id` / `X-Trace-Id` 的生成方式（UUID？nanoid？）待基础设施团队确定。
