# Change: React Testing Library 测试工具封装

## Issue

- GitHub issue: https://github.com/BqLee-AI/QuantAgent/issues/54
- Title: `[FE] 封装 React Testing Library 测试工具`
- Labels: `architecture`, `type:feature`, `priority:medium`, `status:needs-review`, `area:web`, `complexity:medium`
- State: OPEN

## 背景 / 为什么现在做

#53 已经为 `apps/web` 提供 Playwright 浏览器测试基础设施，并预留 Playwright Component Testing 配置。后续 React 组件测试仍需要统一的测试工具层，否则每个测试会重复手写 provider、runtime config、matcher setup 和清理逻辑，容易和生产 `AppProviders` 结构漂移。

本 change 聚焦组件测试的公共入口：基于真实浏览器 CT runner，提供 React Testing Library 相关依赖、统一导出和 `renderWithProviders` helper，让组件测试复用应用级 Provider 组合，同时保持测试之间状态隔离。

## 问题定义

当前 `apps/web` 虽然已经有 Playwright CT 基础设施和一个最小 `PlaceholderPanel` CT 测试，但还没有：

- React Testing Library、jest-dom matcher、user-event 的统一接入。
- 统一的 `apps/web/src/test/render.tsx` 测试导出入口。
- 面向应用 Provider 组合的 `renderWithProviders`。
- RuntimeConfig / provider options 的标准覆盖方式。
- 通过 RTL helper 编写的最小组件渲染测试证明。

现有 `AppProviders` 要求 `config: RuntimeConfig` 和 `queryClient: QueryClient` 两个必传 prop。`renderWithProviders` 不能只包一层 `AppProviders`，还必须在 helper 内部构造 test-safe 的默认 `RuntimeConfig` 和独立 `QueryClient` 实例。

`loadRuntimeConfig` 依赖 `import.meta.env`，且 `apiBaseUrl`、`websocketUrl`、`mode`、`authEnabled` 均为 required。CT 环境不能依赖真实环境变量完成组件渲染，因此 helper 必须内置最小默认 config：`{ apiBaseUrl: '', websocketUrl: '', mode: 'test', authEnabled: false }`。

如果继续让测试直接使用零散导入和手写 wrapper，测试代码会重复且脆弱。

## 目标

- 为 `apps/web` 接入 `@testing-library/react`、`@testing-library/jest-dom` 和 `@testing-library/user-event`。
- 在 Playwright Component Testing 环境中接入 jest-dom matcher 与 RTL cleanup。
- 创建 `apps/web/src/test/render.tsx` 作为组件测试公共入口。
- 实现 `renderWithProviders`，默认复用生产 `AppProviders` 组合。
- 在 `renderWithProviders` 内部使用 test-safe 默认 `RuntimeConfig` 和 `createAppQueryClient()` 创建独立 QueryClient。
- 支持测试覆盖 `RuntimeConfig` 和必要 provider options。
- 从公共入口导出 RTL 常用工具和 `userEvent`，减少测试导入分叉。
- 保留现有 `tests/components/placeholder-panel.spec.tsx` 的 Playwright `mount` 测试，新建 `placeholder-panel-rtl.spec.tsx` 作为 RTL helper 证明。

## 非目标

- 不负责 Playwright E2E 基础设施；该范围由 #53 处理。
- 不测试完整路由流程。
- 不实现 API Client 或网络请求 mock 框架。
- 不为所有页面补齐组件测试。
- 不把 helper 绑定到具体业务页面、接口或模块。
- 不在本 change 中承诺暴露自定义 QueryClient 注入接口；issue 评论已说明 QueryClient 接口暂时未定。
- 不引入 CI/CD 浏览器安装、缓存或流水线执行。

## 影响范围

- `apps/web/package.json` 与 lockfile：新增测试依赖。
- `apps/web/playwright-ct.config.ts` 与 `apps/web/tests/components/setup.ts`：接入 CT-only 测试 setup。
- `apps/web/src/test/render.tsx`：新增测试公共入口。
- `apps/web/tests/components/placeholder-panel-rtl.spec.tsx`：新增 RTL helper 证明测试。
- `apps/web/README.md`：如命令或测试约定变化，需要同步测试说明。

## 依赖和风险

- 依赖 #53 的 Playwright Component Testing 基础设施已经可用。
- 依赖现有 `AppProviders`、`RuntimeConfigProvider` 和 `createAppQueryClient` 保持可测试。
- 风险：RTL 的 DOM matcher 类型与 Playwright CT assertion 类型可能需要清晰分层，避免导入冲突。
- 风险：生产 `AppProviders` 需要 `QueryClient`，helper 必须创建隔离实例，但当前不应公开未定的 QueryClient 自定义 API。
- 风险：CT Vite 配置不包含 TanStack Router plugin，helper 和测试对象不得隐式依赖路由代码生成。

## 实施结论

- `renderWithProviders` 本 change 不暴露自定义 QueryClient 注入接口；后续如需要稳定 QueryClient 自定义 API，应由单独 change 定义。
- Playwright CT setup 固定放在 `apps/web/tests/components/setup.ts`，并由 `playwright-ct.config.ts` 引用。
- 组件测试默认走 RTL `render` 和 `renderWithProviders`；Playwright `mount` 仅用于 CT runner 自身验证或需要 Playwright 特定挂载能力的场景。
- 现有 `placeholder-panel.spec.tsx` 的 Playwright `mount` 测试保留不动，新建 `placeholder-panel-rtl.spec.tsx` 验证 RTL helper。

## 验收口径

- 必须成立：
  - 组件测试可以通过 `renderWithProviders` 渲染 React 组件。
  - helper 默认复用应用级 Provider 组合，不需要每个组件测试重复手写 Provider。
  - helper 内部提供 test-safe 默认 `RuntimeConfig`，不依赖 CT 环境存在真实 `import.meta.env`。
  - helper 内部为每次 render 创建独立 QueryClient。
  - 测试之间不共享脏状态；每次 render 使用独立 provider 状态。
  - jest-dom matcher 可用。
  - `userEvent` 可从测试公共入口使用。
  - 新增 `placeholder-panel-rtl.spec.tsx` 最小渲染测试通过，现有 `placeholder-panel.spec.tsx` 保持作为 Playwright `mount` proof。
- 明确不要求：
  - 不覆盖完整路由集成测试。
  - 不覆盖 API Client 网络行为。
  - 不要求所有组件迁移到该 helper。
  - 不要求当前暴露 QueryClient 自定义接口。
- 失败信号：
  - 每个组件测试仍需要重复手写 Provider。
  - 测试之间共享 provider 状态导致污染。
  - helper 依赖具体业务页面或接口。
  - RTL、jest-dom、Playwright CT 的职责边界不清，导致测试导入方式分裂。

## 验证要求

- `bun run --cwd apps/web test:ct`
- `bun run lint`
- `bun run build --filter=web`
- `openspec validate web-rtl-test-utils --type change --strict --json`
