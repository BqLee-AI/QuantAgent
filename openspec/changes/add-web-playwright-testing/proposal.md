# Change: 接入 Web Playwright 浏览器测试基础设施

## Source

- GitHub issue: https://github.com/BqLee-AI/QuantAgent/issues/53
- Labels: `architecture`, `type:feature`, `priority:medium`, `status:needs-review`, `area:web`, `complexity:medium`
- State: OPEN

## Why

`apps/web` 当前已有 React + Vite + Bun 的前端基础结构，也已经具备 Vitest Node 级纯逻辑测试链路，但仍缺少稳定的真实浏览器自动化测试入口。后续页面状态、Provider、路由行为、浏览器 API 依赖和关键交互流程，都需要在真实浏览器环境中验证；如果继续只依赖手动检查，页面渲染、运行时配置和浏览器行为在后续接入真实功能后很容易漂移。

此外，#54 的浏览器组件测试和 #55 的浏览器 route mock 都依赖一个先行存在的 Playwright 基础设施。如果 #53 不先明确测试边界、目录约定和启动方式，后续多个测试相关 issue 会在 runner、目录结构和职责上反复分叉。

## Problem

`apps/web` 当前没有 Playwright 测试运行器、浏览器项目配置、标准浏览器测试命令、报告输出和最小 smoke test。仓库因此缺少一条可复用的浏览器级测试基础链路，导致：

- 真实浏览器渲染与交互缺少自动化验证入口。
- #54 无法直接在既有浏览器测试基础上接入 Component Testing。
- #55 无法稳定依赖浏览器级 route mock 运行环境。
- 前端测试边界在 Vitest Node、Playwright E2E、Playwright Component Testing 之间不够清晰。

## Goals

- 为 `apps/web` 接入 Playwright 作为真实浏览器测试框架。
- 增加 Playwright 配置，覆盖本地 Vite web server、Chromium 浏览器项目、trace/screenshot/video 策略和报告输出。
- 在 `apps/web/package.json` 增加标准浏览器测试命令。
- 添加一个最小 smoke test，验证 Web app 能在真实 Chromium 浏览器中打开并渲染应用壳层。
- 启用 Playwright Component Testing 的基础配置，供 #54 直接复用。
- 为后续浏览器级 route mock、页面状态验证和组件浏览器测试保留清晰目录约定与扩展点。
- 补充简短测试说明，记录命令、测试目录、调试方式和测试边界。

## Non-Goals

- 不封装 `renderWithProviders` 或 React Testing Library 工具；该范围由 #54 处理。
- 不为所有业务页面补齐完整 E2E。
- 不实现 API Client 或网络层 mock 框架；该范围由 #55 处理。
- 不负责 API Client 纯逻辑单测 runner；该范围已由 Vitest Node runner change 承接。
- 不设置强制覆盖率阈值。
- 不在本 change 内接入 CI/CD 浏览器安装与流水线执行。
- 不扩展 Firefox 或 WebKit 浏览器矩阵；首轮仅考虑 Chromium。

## Known Context

- 当前前端入口在 `apps/web`，技术栈为 React + Vite + Bun。
- `apps/web/vite.config.ts` 已存在 Vite 配置，并已接入 TanStack Router、React 与 Tailwind 插件。
- `apps/web/vite.config.ts` 已配置 `@` → `./src` alias；Playwright Component Testing 底层仍走 Vite，需要确保 CT 环境继续解析同一 alias。
- `apps/web/package.json` 当前存在 `test:unit` / `test:unit:watch`，但没有 Playwright 相关命令。
- `apps/web` 当前已有 `vitest.config.ts`，用于 Node 环境纯逻辑测试；浏览器测试需要保持与其职责边界分离。
- 已归档的 `add-vitest-node-runner` change 已明确：Vitest Node 负责纯逻辑测试，并已通过 `exclude` 排除 `tests/**` 与 `e2e/**`。
- `apps/web/src/routes/__root.tsx` 已渲染 `MainLayout` 与 Router Devtools，适合作为首个 smoke test 的真实页面入口。
- `apps/web/src/routes/events/index.tsx` 已有稳定的页面标题与描述文案，可作为最小页面渲染断言的候选目标。
- #54 将处理 React Testing Library 测试工具封装，并应建立在本 change 提供的 Playwright Component Testing 基础之上。
- #55 将提供网络层 mock helper；其中 Playwright route mock 会依赖本 change 的浏览器测试基础。
- 浏览器测试相关命令和依赖需统一使用 Bun 生态，不引入 `npx`、`npm`、`yarn` 或 `pnpm`。

## What Changes

- 在 `apps/web` 添加 Playwright 所需开发依赖与配置文件。
- 为 E2E 命令采用固定端口 `5173` 与可复用本地 Vite server 的生命周期管理策略，避免本地端口漂移导致调试复杂度上升。
- 验证 `dev` script 的参数转发与当前 Bun 版本兼容性；若 `bun --cwd apps/web run dev -- --host 127.0.0.1 --port 5173` 不稳定，则通过 Bun 生态下的本地包装脚本显式托管 Vite 生命周期。
- 配置浏览器项目仅包含 Chromium，并明确保留未来扩展 Firefox/WebKit 的位置，但不在本 change 启用。
- 配置标准浏览器测试命令，例如 `test:e2e`、`test:e2e:ui`、`test:e2e:debug`。
- 复用现有 Vite `resolve.alias` 约定，确保 Playwright Component Testing 环境继续解析 `@` → `./src`。
- 启用 Playwright Component Testing 的基础配置与目录约定，使 #54 可直接在既有 runner 上增加组件测试用例。
- 为 E2E smoke test 和 Component Testing 采用分层目录：`apps/web/e2e/` 承载页面级浏览器测试，`apps/web/tests/components/` 承载 CT 用例，避免与现有 Vitest `src/**/*.test.ts` 规则冲突。
- 配置 HTML 报告与必要的 trace/screenshot/video 保留策略，支持失败定位。
- 添加最小 smoke test，验证应用可在真实 Chromium 中打开并渲染出可识别的应用壳层或页面内容。
- 补充测试说明文档，明确 Vitest Node、Playwright E2E、Playwright Component Testing 的职责边界。

## Impact

- 影响目录：`apps/web/**`、`openspec/changes/add-web-playwright-testing/**`。
- 本 change 的首个直接消费者是 #54：其浏览器组件测试需要先依赖本 change 提供的 CT 基础承载。
- #8 的纯逻辑测试已先由 `add-vitest-node-runner` change 承接，因此本 change 不作为 #8 的首个执行基础设施。
- #55 是更下游的消费者：其 Playwright route mock 依赖本 change 落地后的浏览器测试目录和 runner 约定。
- 直接受益 issue：#54、#55，以及后续所有需要真实浏览器环境的 Web 测试需求。
- 与已归档的 `add-vitest-node-runner` change 构成互补：前者负责 Node 纯逻辑测试，本 change 负责 Chromium 浏览器测试与组件测试基础。

## Dependencies And Risks

- 无明确前置依赖，可独立完成。
- 需要保持 Playwright 与 Vitest Node 的目录、命令和职责边界清晰，避免 runner 相互误收集测试文件。
- 需要确保本地 E2E 包装脚本的启动与复用策略和当前 `apps/web` 的 Vite dev server 行为兼容。
- 需要验证 Bun 对 `bun --cwd apps/web run dev -- --host 127.0.0.1 --port 5173` 这类参数转发是否稳定支持；若不兼容，需切换到 Bun 生态内的本地包装脚本或等效方案。
- 启用 Component Testing 会引入额外配置面，需要在 spec 中先明确其只提供基础承载，不提前封装组件测试 helper。
- `tanstackRouter({ autoCodeSplitting: true })` 在 CT 场景下可能触发路由代码生成或与组件挂载流程冲突，需要验证 CT 是否可直接复用当前 `vite.config.ts`，或是否需要独立 Vite 配置并排除路由插件。
- 如果 CT 使用独立 Vite 配置，仍需保持 `@` → `./src` alias 与主应用一致，避免测试环境和运行环境解析漂移。
- CI/CD 暂不纳入本 change，意味着实现阶段只能先保证本地开发链路和文档约定完整。

## Resolved Decisions

- 浏览器矩阵首轮固定为 Chromium，不同时启用 Firefox 或 WebKit。
- CI/CD 浏览器安装与流水线执行不纳入本 change，后续单独规划。
- Playwright Component Testing 在本 change 中启用基础配置，供 #54 直接接入。

## Success Criteria

- `bun run --cwd apps/web test:e2e` 可以启动或复用本地 web server，并通过至少一个 Chromium smoke test。
- Playwright 报告可生成并能用于定位失败。
- smoke test 验证真实浏览器中的应用壳层或页面内容渲染，而不是只断言空页面。
- `apps/web` 中存在可供 #54 直接复用的 Playwright Component Testing 基础配置。
- 文档能明确说明 Vitest Node、Playwright E2E、Playwright Component Testing 的职责边界。

## Verification

- `bun run --cwd apps/web test:ct`
- `bun run --cwd apps/web test:e2e`
- `bun run --cwd apps/web test:e2e:ui`
- `bun run lint`
- `bun run build --filter=web`
