# Vitest Node Runner Specification

## ADDED Requirements

### Requirement: Vitest Node Runner For Web Unit Tests

`apps/web` SHALL 提供一个基于 Vitest 的 Node 环境单元测试 runner，用于执行纯 TypeScript 逻辑测试。

#### Scenario: Node-only unit runner exists

- **WHEN** 开发者在 `apps/web` 中执行 unit test 命令
- **THEN** 测试在 Node 环境运行
- **AND** 不需要启动浏览器
- **AND** 不依赖 Playwright

#### Scenario: Clear boundary from browser tests

- **WHEN** 开发者查阅本 change 的文档或 spec
- **THEN** 能明确区分 Vitest Node runner 与 #53 Playwright 浏览器测试的职责边界
- **AND** 能明确区分本 runner 与 #54 浏览器组件测试工具链的职责边界

### Requirement: Standard Unit Test Commands

`apps/web/package.json` SHALL 暴露标准 unit test scripts。

#### Scenario: Unit command available

- **WHEN** 开发者运行 `bun --cwd apps/web run test:unit`
- **THEN** Vitest 执行纯逻辑单元测试并返回成功/失败状态码

#### Scenario: Watch command available

- **WHEN** 开发者运行 `bun --cwd apps/web run test:unit:watch`
- **THEN** Vitest 以 watch 模式运行，便于本地迭代

### Requirement: Vitest Config Strategy

Vitest 配置 SHALL 使用独立 `apps/web/vitest.config.ts`，而不是把 unit test 配置直接并入现有 `vite.config.ts`。

#### Scenario: Standalone Vitest config exists

- **WHEN** 开发者检查 `apps/web` 的测试配置
- **THEN** 存在独立的 `vitest.config.ts`
- **AND** 该文件定义 unit runner 所需的 `test` 配置

#### Scenario: Browser build plugins stay out of Node unit runner

- **WHEN** 开发者检查 `vitest.config.ts` 与 `vite.config.ts`
- **THEN** Vitest 不要求继承 `tanstackRouter`、`react`、`tailwindcss` 这些面向浏览器构建的插件链
- **AND** Node unit runner 仅保留纯逻辑测试所需的最小配置

### Requirement: Co-located Test File Convention

纯逻辑测试文件 SHALL 与被测文件放在同一目录，统一采用 `*.test.ts` 命名。

#### Scenario: Test file matching rule

- **WHEN** 开发者在 `apps/web/src/shared/config/runtime.test.ts` 这类位置创建测试文件
- **THEN** `test:unit` 命令会自动匹配并执行该文件

#### Scenario: Unit test glob excludes non-unit directories

- **WHEN** Vitest 扫描 `apps/web` 下的测试文件
- **THEN** 必须排除 `node_modules` 与 `dist`
- **AND** 必须排除未来 Playwright 可能使用的 `tests/` 与 `e2e/` 目录
- **AND** 不因 #53 完成后的浏览器测试目录而误收集非 unit test 文件

#### Scenario: No centralized unit test directory required

- **WHEN** 开发者检查 unit test 约定
- **THEN** 不要求把测试集中放到 `apps/web/src/test/unit/`
- **AND** 以被测模块旁边 co-located 方式作为默认规范

### Requirement: TypeScript Path Alias Compatibility

Vitest 配置 SHALL 与 `apps/web` 当前的 TypeScript alias 约定保持一致。

#### Scenario: Existing @ alias resolves in Vitest

- **WHEN** `apps/web/tsconfig.app.json` 定义 `@/*` → `./src/*`
- **THEN** `vitest.config.ts` 中也能解析 `@` 指向 `apps/web/src`
- **AND** 使用 `@/` 导入的纯逻辑模块可在 unit test 中直接运行

#### Scenario: Alias strategy matches current repo shape

- **WHEN** 开发者检查 alias 配置
- **THEN** 当前 change 通过 `resolve.alias` 保持与 `vite.config.ts` 一致
- **AND** 不要求仅为单个 `@` alias 引入 `vite-tsconfig-paths`

### Requirement: Pure Logic Coverage Scope

该 runner SHALL 覆盖 `apps/web` 的纯逻辑模块测试，而不是浏览器渲染测试。

#### Scenario: TypeScript logic module testable

- **WHEN** 模块不依赖 DOM 或浏览器 API
- **THEN** 开发者可以使用该 runner 为其编写并运行单元测试

#### Scenario: Browser rendering out of scope

- **WHEN** 测试目标是 React 组件渲染、浏览器交互或真实页面行为
- **THEN** 不应要求通过本 runner 覆盖
- **AND** 应转由 #53 或 #54 对应基础设施承接

### Requirement: Smoke Test Proof

仓库 SHALL 包含至少一个最小 smoke unit test，用于证明 runner、脚本和 glob 配置有效。

#### Scenario: Smoke test passes

- **WHEN** 开发者首次完成本 change 并运行 `bun --cwd apps/web run test:unit`
- **THEN** 至少有一个 `*.test.ts` 被执行并通过
- **AND** 该测试位于 `apps/web/src/shared/config/runtime.test.ts`
- **AND** 其被测目标为 `apps/web/src/shared/config/runtime.ts`

### Requirement: Support For Issue #8 And #55

本 runner SHALL 被定义为 #8 和 #55 的纯逻辑测试基础设施。

#### Scenario: Issue #8 is the first consumer

- **WHEN** 本 runner 首次落地
- **THEN** #8 的 Tier 1 / Tier 2 API Client 测试是首个直接消费者
- **AND** 本 change 优先为其提供可执行的 Node 单元测试基础设施

#### Scenario: Api client tests can depend on this runner

- **WHEN** 开发者实现 #8 的 Tier 1 / Tier 2 测试
- **THEN** 可以直接复用本 Vitest Node runner

#### Scenario: Issue #55 is a later consumer

- **WHEN** 开发者后续实现 #55 的 `mockEnvelope.ts` 测试
- **THEN** 该测试复用本 Vitest Node runner
- **AND** 其实施顺序不先于 #8 对本 runner 的消费

#### Scenario: Mock envelope tests can depend on this runner

- **WHEN** 开发者实现 #55 的 `mockEnvelope.ts` 测试
- **THEN** 可以直接复用本 Vitest Node runner

### Requirement: Axios Interceptor Test Strategy

API Client interceptor 测试策略 SHALL 明确采用 Axios adapter mock。

#### Scenario: Interceptor tests use adapter mock

- **WHEN** 开发者实现 #8 的 interceptor 行为测试
- **THEN** 通过 Axios adapter mock 驱动请求/响应场景
- **AND** 不以 mock axios instance 作为规范要求

### Requirement: Build And Lint Compatibility

引入 Vitest 后，`apps/web` 现有前端构建和静态检查 SHALL 继续可用。

#### Scenario: Lint and build remain green

- **WHEN** 完成本 change
- **THEN** `bun run lint` 通过
- **AND** `bun run build --filter=web` 通过
