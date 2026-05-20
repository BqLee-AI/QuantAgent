## MODIFIED Requirements

### Requirement: Test Directory Separation

浏览器测试目录 SHALL 与现有 Vitest Node unit test 目录约定清晰分离，并为共享网络 mock 工具保留测试资产边界。

#### Scenario: Existing Vitest exclude keeps directories isolated
- **WHEN** 开发者检查现有 `vitest.config.ts`
- **THEN** 其中已排除 `tests/**` 与 `e2e/**`
- **AND** Playwright 页面测试放在 `e2e/**`
- **AND** Playwright Component Testing 放在 `tests/components/**`

#### Scenario: Browser test naming stays separate from unit tests
- **WHEN** 开发者同时维护 Vitest 与 Playwright 测试
- **THEN** Vitest 继续匹配 `src/**/*.test.ts`
- **AND** Playwright CT 使用 `tests/components/**/*.spec.tsx`
- **AND** 目录与命名共同保证两类 runner 不会互相误收集

#### Scenario: Route mock extension point preserved
- **WHEN** #55 在浏览器测试边界内引入共享 network mock utilities
- **THEN** `apps/web/e2e/mocks/**` 继续作为 Playwright route mock 的扩展位置
- **AND** 页面级测试仍位于 `apps/web/e2e/**`

#### Scenario: Shared network mock utilities stay under test assets
- **WHEN** #55 引入 `mockEnvelope.ts` 与 `route-mock.ts`
- **THEN** 这些工具保持在 `apps/web` 测试目录边界内
- **AND** 浏览器 route 拦截层优先对齐 `apps/web/e2e/mocks/**`
- **AND** 不进入应用运行时代码导出面
