# Change: API Client 与全局错误治理

## Why

前端数据层缺乏统一的 HTTP 客户端封装，当前各页面/组件直接使用裸 fetch 或 TanStack Query，存在以下问题：
- 无统一 baseURL、timeout、鉴权注入，请求配置分散。
- 后端响应 envelope（`{ code, data, msg }`）的解包逻辑在各处重复实现。
- 401 Token 过期后无静默刷新机制，用户需手动重新登录。
- 业务错误码无集中注册表，错误处理行为不一致。
- 缺少 AbortController 取消支持，组件卸载时可能产生竞态请求。

本 change 封装一个强类型 `apiClient`，基于原生 Fetch（不引入 Axios），集成鉴权、响应解包、401 静默刷新和全局错误治理，为 TanStack Query 等上层消费者提供可靠的数据层基础。

## What Changes

- **`apps/web/src/shared/api/types.ts`**：定义响应 envelope、请求配置、token provider 等核心类型。
- **`apps/web/src/shared/api/token.ts`**：封装 token 存取逻辑，支持 localStorage/sessionStorage 可切换的 token provider，Token Auth 开关（默认开发阶段关闭）。
- **`apps/web/src/shared/api/errors.ts`**：定义 `ApiError` 类（含 code、msg、request_id、trace_id、status），以及业务错误码注册表（error-to-UI-behavior 映射）。
- **`apps/web/src/shared/api/client.ts`**：基于 Fetch 的 `apiClient` 封装，包含：
  - `get<T>` / `post<TBody, TResponse>` / `put` / `patch` / `del` 方法
  - `requestEnvelope<T>()` 方法返回完整 `{ code, data, msg }` envelope
  - baseURL 默认 `/api/v1`，timeout 10s
  - `authEnabled=true` 时注入 `Authorization: Bearer <token>`，默认开发阶段关闭
  - code === 0 时自动解包返回 `T`；code !== 0 时抛 `ApiError`
  - 401 静默刷新（共享 refresh promise，避免并发刷新）
  - AbortController signal 支持
  - Trace header（仅 TODO 预留 `X-Request-Id` / `X-Trace-Id`）
  - 内部请求前处理 pipeline（auth 注入、trace TODO）和响应后处理 pipeline（envelope 解包、ApiError 转换、401 refresh），不暴露 Axios 风格可插拔 interceptor API
- **`apps/web/src/shared/api/index.ts`**：统一导出。
- **`packages/contracts`**：预留类型入口（`.gitkeep` 已存在），不实现生成流程。

## Out Of Scope

- 不引入 Axios 依赖（使用原生 Fetch）。
- Trace header 只预留 TODO，不实现真实 trace ID 生成逻辑。
- 不实现 UI 层 toast/modal 弹窗（error registry 只定义行为映射，UI 消费留给后续 issue）。
- 不实现跨业务的全局请求缓存/去重；TanStack Query 负责 query 层重复请求合并。apiClient 仅实现 401 refresh 并发去重，避免多个 401 同时触发多次 refresh。非 Query 场景的通用请求去重后续单独设计。
- 不暴露 Axios 风格可插拔 interceptor API；在 Fetch wrapper 内实现等价的请求前处理和响应后处理 pipeline，包括 auth 注入、trace TODO、envelope 解包、ApiError 转换和 401 refresh。
- 后端 error code 类型定义待与后端对齐，本 change 只定义前端侧框架。

## Success Criteria

- `apiClient.get<User>('/me')` 成功时返回 `User` 类型。
- `apiClient.requestEnvelope<User>('/me')` 返回完整 `{ code, data, msg }` envelope。
- 后端返回非 0 code 时抛出 `ApiError`，包含 code、msg、request_id、trace_id。
- 401 响应触发静默刷新，并发请求共享同一 refresh promise。
- Token Auth 默认关闭，可通过配置开启。
- `bun run build --filter=web` 通过。

## Testing Strategy

- 单元测试覆盖 token provider、ApiError、error registry。
- fetch mock 测试覆盖：成功解包、完整 envelope 返回、业务错误（code !== 0）、HTTP 错误（非 2xx）、timeout abort、AbortController signal abort。
- 401 refresh 测试覆盖：单请求刷新重放、并发 401 共享 refreshPromise、刷新失败清 token + 调用 onUnauthorized。
- auth 开关测试覆盖：默认不注入 Authorization、authEnabled=true 时注入 Bearer token。
- trace header 只验证 TODO 注释或预留函数位置，不验证真实 header。
- 类型验证通过 `bun run build --filter=web`。
- 若仓库尚未配置测试框架，本 change 应补充最小测试运行能力（vitest 或等价工具），确保 401 并发 refresh 等关键路径有自动化验证。

## Open Questions

- **后端 error code 类型**：需与后端确认业务错误码的完整枚举（如风控错误、限流错误等），当前 registry 仅定义框架和占位。
- **Token 刷新接口契约**：刷新接口路径、请求/响应格式待后端确认，当前提供可配置 `refreshToken` 函数。
- **Trace header 生成策略**：`X-Request-Id` / `X-Trace-Id` 的生成方式（UUID？nanoid？）待基础设施团队确定。
