# Web Playwright Testing Specification

## ADDED Requirements

### Requirement: Playwright Chromium Browser Test Runner

`apps/web` SHALL 提供一个基于 Playwright 的真实浏览器测试 runner，用于执行 Chromium 浏览器环境下的页面与交互验证。

#### Scenario: Chromium browser runner exists

- **WHEN** 开发者在 `apps/web` 中执行浏览器测试命令
- **THEN** 测试在真实 Chromium 浏览器环境运行
- **AND** 不依赖 Vitest Node runner 充当浏览器测试承载

#### Scenario: Browser matrix is intentionally scoped

- **WHEN** 开发者检查 Playwright 项目配置
- **THEN** 首轮仅启用 Chromium 项目
- **AND** 不要求同时启用 Firefox 或 WebKit

### Requirement: Standard Browser Test Commands

`apps/web/package.json` SHALL 暴露标准 Playwright 浏览器测试脚本。

#### Scenario: Headless test command available

- **WHEN** 开发者运行 `bun run --cwd apps/web test:e2e`
- **THEN** Playwright 执行浏览器测试并返回成功或失败状态码

#### Scenario: Interactive ui command available

- **WHEN** 开发者运行 `bun run --cwd apps/web test:e2e:ui`
- **THEN** Playwright 以 UI 模式启动，便于本地调试

#### Scenario: Debug command available

- **WHEN** 开发者运行 `bun run --cwd apps/web test:e2e:debug`
- **THEN** Playwright 以适合断点和逐步检查的调试模式运行

### Requirement: Playwright Config File Strategy

浏览器 E2E 与 Component Testing SHALL 保持清晰的配置边界，并继续共享一致的目录约定、浏览器项目约定与报告策略。

#### Scenario: Config files stay scoped by test type

- **WHEN** 开发者检查 `apps/web` 的 Playwright 配置
- **THEN** 页面级 E2E 使用 `playwright.config.ts`
- **AND** Component Testing 使用独立的 `playwright-ct.config.ts`

#### Scenario: Separate configs keep shared conventions aligned

- **WHEN** 开发者审阅配置方案
- **THEN** E2E 与 CT 仍保有独立的 `testDir`、文件匹配规则和项目级 `use` 配置
- **AND** 两者继续共享 Chromium-only、报告输出与目录边界约定

### Requirement: Local Vite Server Integration

浏览器测试命令 SHALL 能自动启动或复用 `apps/web` 的本地 Vite dev server。

#### Scenario: Web server bootstraps automatically

- **WHEN** 开发者运行 `bun run --cwd apps/web test:e2e`
- **THEN** 浏览器测试命令会启动或复用 `apps/web` 的 Vite server
- **AND** 浏览器测试无需开发者手工先启动独立 server

#### Scenario: Server command stays aligned with current app entry

- **WHEN** 开发者检查本地浏览器测试启动方案
- **THEN** 启动命令基于 `apps/web` 现有 `dev` script 或本地 Vite CLI
- **AND** 不要求为本 change 重构应用启动方式

#### Scenario: Fixed port and reuse strategy are explicit

- **WHEN** 开发者检查本地浏览器测试启动方案
- **THEN** E2E 固定使用 `127.0.0.1:5173`
- **AND** 命令会复用已存在的本地 Vite server

#### Scenario: Fallback command stays inside Bun ecosystem

- **WHEN** `bun --cwd apps/web run dev -- --host 127.0.0.1 --port 5173` 无法稳定向 `vite` 转发参数
- **THEN** 浏览器测试命令可切换到基于 Bun 生态的本地包装脚本或 `bunx vite --host 127.0.0.1 --port 5173`
- **AND** 不引入 `npx`、`npm`、`yarn` 或 `pnpm`

### Requirement: Playwright Browser Installation

本地首次运行前 SHALL 完成 Chromium 浏览器二进制安装。

#### Scenario: Chromium binary available before first run

- **WHEN** 开发者首次在本机执行 `bun run --cwd apps/web test:e2e`
- **THEN** Chromium 浏览器二进制已经可用
- **AND** 安装步骤默认使用 `bunx playwright install chromium` 或等效 Bun 命令
- **AND** 在 Linux 环境下可按需追加 `--with-deps` 以安装系统依赖

#### Scenario: Missing browser yields actionable guidance

- **WHEN** 开发者尚未安装 Chromium 浏览器二进制就执行浏览器测试命令
- **THEN** 命令输出必须能指向明确的安装动作
- **AND** 不允许以无法定位的浏览器启动失败结束

### Requirement: Browser Smoke Test Proof

仓库 SHALL 包含至少一个最小 Chromium smoke test，用于证明真实浏览器链路可用。

#### Scenario: Smoke test proves app shell renders

- **WHEN** 开发者首次完成本 change 并运行 `bun run --cwd apps/web test:e2e`
- **THEN** 至少有一个浏览器 smoke test 被执行并通过
- **AND** 该测试验证应用壳层、稳定页面标题或稳定页面说明文案已渲染
- **AND** 不只是断言空白页面或 HTTP 200

#### Scenario: Smoke assertion targets current Events route content

- **WHEN** 开发者选择 smoke test 的断言目标
- **THEN** 应断言 `src/routes/events/index.tsx` 渲染的稳定文案
- **AND** 推荐断言 `.page-title` 的文本为 `Events`
- **AND** 或断言 `.page-kicker` 的文本为 `Event Inbox`

### Requirement: Failure Diagnostics And Report Output

Playwright 测试 SHALL 生成可用于失败定位的报告与诊断产物。

#### Scenario: Html report generated

- **WHEN** 浏览器测试执行完成
- **THEN** 开发者可查看 Playwright 报告以定位失败

#### Scenario: Diagnostic artifacts retained only when useful

- **WHEN** 测试失败或进入重试
- **THEN** trace、screenshot、video 按需保留
- **AND** 不要求在所有成功测试上无差别保留全部重型产物

### Requirement: Component Testing Base Enabled

本 change SHALL 启用 Playwright Component Testing 的基础配置，供后续组件测试直接接入。

#### Scenario: Component testing is enabled as infrastructure

- **WHEN** 开发者检查浏览器测试配置
- **THEN** 仓库中已存在 Playwright Component Testing 项目配置
- **AND** CT 使用 `playwright-ct.config.ts`
- **AND** CT 项目的 `testDir` 为 `tests/components`
- **AND** CT 测试文件使用 `*.spec.tsx` 命名
- **AND** #54 可以在此基础上添加组件测试文件

#### Scenario: Component testing stays scoped

- **WHEN** 开发者审阅本 change 的范围
- **THEN** 本 change 只负责启用 Component Testing 基础设施
- **AND** 不要求在本 change 中封装 React Testing Library helper 或业务组件测试模板

#### Scenario: CT Vite strategy is validated explicitly

- **WHEN** 开发者接入 Component Testing
- **THEN** CT 优先复用现有 Vite 配置中的 React、Tailwind 与 alias 约定
- **AND** 需要验证 `tanstackRouter({ target: "react", autoCodeSplitting: true })` 是否会在 CT 场景中触发路由代码生成或组件挂载异常
- **AND** 若该插件与 CT 冲突，则允许为 CT 提供独立 Vite 配置并排除路由插件

### Requirement: Path Alias Compatibility

Playwright Component Testing 环境 SHALL 继续解析主应用的 `@` 路径别名。

#### Scenario: Existing @ alias resolves in CT

- **WHEN** CT 测试文件使用 `@/` 导入 `apps/web/src` 下的模块
- **THEN** `@` 仍解析到 `./src`
- **AND** 解析结果与主应用 Vite 配置保持一致

#### Scenario: Alias remains aligned if CT uses separate Vite config

- **WHEN** CT 因路由插件兼容性采用独立 Vite 配置
- **THEN** 独立配置仍保留 `@` → `./src` alias
- **AND** 不允许 CT 与主应用产生不同的模块解析约定

### Requirement: Test Directory Separation

浏览器测试目录 SHALL 与现有 Vitest Node unit test 目录约定清晰分离。

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

- **WHEN** 后续 #55 需要引入 Playwright route mock
- **THEN** 浏览器测试目录结构中已保留清晰的扩展位置
- **AND** 本 change 不需要先实现具体 mock helper

### Requirement: Clear Boundary Across Test Layers

仓库文档或 spec SHALL 明确区分 Vitest Node、Playwright E2E、Playwright Component Testing 三类测试职责。

#### Scenario: Pure logic tests stay on Vitest

- **WHEN** 测试目标是纯 TypeScript 逻辑、数据转换或不依赖浏览器的模块
- **THEN** 该测试应继续由 Vitest Node runner 承接

#### Scenario: Page behavior tests use Playwright

- **WHEN** 测试目标是真实页面渲染、浏览器 API、路由联动或端到端交互
- **THEN** 该测试应由 Playwright 浏览器 runner 承接

#### Scenario: Component browser tests build on this base

- **WHEN** 测试目标是浏览器环境下的组件级渲染与交互
- **THEN** 该测试应建立在本 change 启用的 Playwright Component Testing 基础设施之上

### Requirement: CI Is Deferred But Not Blocked

本 change SHALL 以本地可执行链路为验收目标，同时明确 CI/CD 接入延后。

#### Scenario: Local execution is required now

- **WHEN** 本 change 完成
- **THEN** 本地开发者必须能在机器上执行 Playwright 浏览器测试命令

#### Scenario: CI integration is explicitly out of scope

- **WHEN** 开发者审阅本 change 的验收范围
- **THEN** 不要求在当前 change 中完成 CI/CD 浏览器安装、缓存或流水线执行
- **AND** 后续可以在独立 issue 或 change 中补充

### Requirement: Build And Lint Compatibility

引入 Playwright 后，`apps/web` 现有构建与静态检查 SHALL 继续可用。

#### Scenario: Lint and build remain green

- **WHEN** 完成本 change
- **THEN** `bun run lint` 通过
- **AND** `bun run build --filter=web` 通过
