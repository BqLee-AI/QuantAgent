## Why

#8 后续会拆出 API Client、错误转换、401 恢复和页面级网络行为测试。如果前端测试没有统一的网络 mock 框架，单元测试和浏览器测试会继续各自手写 fake、route 拦截或依赖真实后端，导致响应 envelope 与错误场景无法复用。

issue #55 先只收敛“前端网络 mock 测试底座”，为后续 API Client 与页面测试提供统一的测试资产和场景表达，不在本 change 中实现真实网络层能力。

## What Changes

- 为 `apps/web` 增加统一的网络层测试 mock 能力，覆盖纯数据 envelope 构造和 Playwright 浏览器 route mock 两层。
- 定义 `mockEnvelope.ts` 的职责边界：它是纯数据 envelope 构造层，提供成功响应、业务错误、HTTP error、network failure 和 unauthorized 等可复用构造函数，不依赖 Playwright。
- 定义 `route-mock.ts` 的职责边界：它是 Playwright route 拦截层，基于 `page.route` 封装浏览器测试拦截，并复用 `mockEnvelope.ts`，不能维护第二套响应格式。
- 对齐现有 `apps/web` 测试体系边界：网络 mock 资产位于 `apps/web` 测试目录内，优先对齐现有 `apps/web/e2e/mocks/README.md` 预留的浏览器 mock 扩展位，并服务于 `apps/web/e2e/**`、`apps/web/tests/**` 和 `apps/web/src/**/*.test.ts`。
- 为 401 recover 仅预留 helper 边界和场景入口；不实现真实 refresh endpoint、cookie 行为或请求重放流程。
- 增加最小测试证明，确认页面测试可以拦截 `/api/v1/*` 请求并返回统一 envelope。

## Capabilities

### New Capabilities
- `web-api-mock-framework`: 定义前端网络层测试的统一 envelope mock 与 Playwright route mock 框架。

### Modified Capabilities
- `web-playwright-testing`: 扩展浏览器测试基础设施的 requirement，增加网络 route mock 扩展位与目录边界约束。

## Impact

- `apps/web/e2e/mocks/**`：共享网络 mock 工具和示例 fixture 的首选落位。
- `apps/web/e2e/**`、`apps/web/tests/**`、`apps/web/src/**/*.test.ts`：复用统一网络 mock 资产的测试消费边界。
- `apps/web` 测试命令与测试说明：补充如何在页面测试和后续 API Client 测试中复用 mock 工具。
- `openspec/specs/web-playwright-testing/spec.md`：补充 route mock 扩展 requirement。
- 后续依赖方包括 #8 的 API Client、错误治理和页面级网络测试，但本 change 不实现这些业务能力本身。
