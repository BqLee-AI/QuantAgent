## ADDED Requirements

### Requirement: Shared Network Mock Envelope Utilities

`apps/web` SHALL 提供独立于 Playwright 的网络 mock envelope 构造工具，供前端单元测试与浏览器测试共享。

#### Scenario: Success envelope can be constructed without browser runtime
- **WHEN** 测试导入 `mockEnvelope.ts` 并构造成功响应
- **THEN** helper 可以返回符合后端 `{ code, data, msg, request_id?, trace_id? }` 约定的响应体
- **AND** 该 helper 不依赖 `page.route`、DOM 或浏览器环境

#### Scenario: Error variants share one envelope contract
- **WHEN** 测试需要表达业务错误、HTTP error、network failure 或 unauthorized 场景
- **THEN** helper 使用统一命名与统一 envelope 约定表达这些场景
- **AND** 测试不需要手写分散的 `{ code, data, msg }` 结构

#### Scenario: HTTP error and network failure stay distinct
- **WHEN** 测试需要表达服务端返回失败响应
- **THEN** HTTP error 表示存在明确的 HTTP status 和响应体
- **AND** network failure 表示请求层失败、连接中断或 `route.abort` 一类没有正常 HTTP 响应体的场景

### Requirement: Playwright Route Mock Reuses Envelope Utilities

`apps/web` SHALL 提供基于 Playwright `page.route` 的浏览器网络 mock 封装，并复用共享 envelope 工具。

#### Scenario: Browser tests intercept API routes with shared helpers
- **WHEN** 页面测试注册 `/api/v1/*` 的 route mock
- **THEN** 测试可以通过公共 `route-mock.ts` 封装返回 mock 响应
- **AND** 返回体复用 `mockEnvelope.ts` 的构造结果

#### Scenario: Route mock does not define a second response format
- **WHEN** 开发者检查 `route-mock.ts` 的实现边界
- **THEN** 其中不能维护独立于 `mockEnvelope.ts` 的另一套 envelope 结构
- **AND** 浏览器测试与单元测试看到的响应协议保持一致

#### Scenario: Network failure is expressed through request-layer behavior
- **WHEN** 浏览器测试需要表达 network failure
- **THEN** `route-mock.ts` 使用请求层失败或 `route.abort` 一类方式表达该场景
- **AND** 该场景不能伪装成带正常响应体的 HTTP error

### Requirement: Mock Assets Stay Inside Test Boundaries

网络 mock 工具 SHALL 保持在 `apps/web` 测试资产边界内，不作为运行时代码导出。

#### Scenario: Mock helpers are stored under test directories
- **WHEN** 开发者检查网络 mock 的目录落位
- **THEN** 浏览器 route mock 工具优先对齐 `apps/web/e2e/mocks/**` 扩展位
- **AND** `apps/web/e2e/**`、`apps/web/tests/**` 和 `apps/web/src/**/*.test.ts` 可以复用这些测试资产
- **AND** 这些工具不进入应用运行时代码导出面

### Requirement: Unauthorized And Recover Scenarios Are Reserved

网络 mock 框架 SHALL 为 401 unauthorized 与 recover 测试预留表达能力，但本 change MUST NOT 固化真实 refresh/cookie 实现。

#### Scenario: Unauthorized response can be expressed now
- **WHEN** 测试需要表达请求返回 401 unauthorized
- **THEN** mock helper 可以构造该场景
- **AND** 不要求依赖真实 refresh endpoint 或 cookie 机制

#### Scenario: Recover flow remains an extension point
- **WHEN** 开发者检查 401 recover 相关 helper
- **THEN** helper 只预留首次 401、recover 成功或失败、并发 401 共享 recover 的测试场景入口
- **AND** 本 change 不固定具体业务 endpoint、cookie 行为或最终请求重放实现
- **AND** 本 change 不实现真实 `apiClient` interceptor 或 refresh 流程

### Requirement: Minimal Browser Proof Exists

仓库 SHALL 包含一个最小浏览器测试证明网络 mock 框架可用于页面测试。

#### Scenario: Page test proves API route interception
- **WHEN** 开发者运行 `bun --cwd apps/web run test:e2e`
- **THEN** 至少有一个页面测试证明 `/api/v1/*` 请求可以被 route mock 拦截
- **AND** 该测试通过统一 envelope helper 返回 mock 响应
- **AND** 测试不依赖真实后端服务启动
