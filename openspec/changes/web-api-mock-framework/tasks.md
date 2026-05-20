## 1. Scope And Boundary

- [x] 1.1 确认 issue #55、issue 评论和父 issue #8 的范围，只交付前端网络 mock 测试底座，不实现 `apiClient`、interceptor、refresh cookie 或业务页面网络治理。
- [x] 1.2 对齐现有 `apps/web` 测试结构，明确 `apps/web/e2e/mocks/**`、`apps/web/e2e/**`、`apps/web/tests/**` 和 `apps/web/src/**/*.test.ts` 的使用边界。

## 2. Mock Utilities

- [x] 2.1 在 `apps/web` 测试体系内创建共享网络 mock 工具目录，并优先对齐 `apps/web/e2e/mocks/README.md` 预留的 route mock 扩展位。
- [x] 2.2 创建 `mockEnvelope.ts`，提供成功响应、业务错误、HTTP error、network failure 和 unauthorized 的纯数据构造函数。
- [x] 2.3 在 helper API 中区分 HTTP error 与 network failure：前者表示带有 HTTP status/响应体的服务端响应，后者表示请求层失败或 `route.abort` 场景。
- [x] 2.4 创建 `route-mock.ts`，封装 Playwright `page.route`，并强制复用 `mockEnvelope.ts`，不得维护第二套响应格式。
- [x] 2.5 为 401 recover 只预留 helper 边界和场景入口，支持表达首次 401、recover 成功或失败、并发 401 共享 recover 的测试意图，不实现真实 refresh/cookie/重放流程。

## 3. Proof And Docs

- [x] 3.1 添加最小浏览器测试示例，证明页面测试可以拦截 `/api/v1/*` 请求并返回统一 envelope。
- [x] 3.2 为 `mockEnvelope.ts` 添加单元测试或最小验证接入点，证明其可被 `apps/web/src/**/*.test.ts` 直接导入且不依赖 Playwright。
- [x] 3.3 更新 `apps/web` 测试说明，记录网络 mock 工具的目录、命名和复用方式。

## 4. Validation

- [x] 4.1 实现后运行 `bun --cwd apps/web run test:unit`，验证纯数据 envelope 构造层可在非 Playwright 环境下使用。
- [x] 4.2 运行 `bun --cwd apps/web run test:e2e`，验证 Playwright route mock 的最小浏览器证明。
- [x] 4.3 运行 `bun --cwd apps/web run build`，验证前端构建通过。
- [x] 4.4 运行 `bun run lint`。
- [x] 4.5 运行 `openspec validate web-api-mock-framework --type change --strict --json`。
