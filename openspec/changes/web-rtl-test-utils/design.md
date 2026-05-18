# Design: React Testing Library 测试工具封装

## 测试入口

新增 `apps/web/src/test/render.tsx` 作为组件测试公共入口。测试文件应优先从该入口导入：

- `renderWithProviders`
- RTL 常用导出，例如 `screen`、`within`、`cleanup`
- `userEvent`

该入口的目标是减少测试导入分叉，并把 provider 组合、默认 runtime config 和测试隔离策略收敛到一个位置。

## Provider 策略

`renderWithProviders` 默认复用生产 `AppProviders`，避免测试 wrapper 与应用真实 provider 栈漂移。helper 每次调用都必须创建独立 provider 状态。

RuntimeConfig 支持测试覆盖。默认 config 应为最小可用配置，覆盖方式应保持浅显，避免测试必须了解应用启动细节。

`AppProviders` 当前要求 `config: RuntimeConfig` 和 `queryClient: QueryClient` 两个必传 prop。`renderWithProviders` 内部负责构造这两个值：RuntimeConfig 来自 test-safe 默认值和测试传入覆盖的合并结果，QueryClient 通过 `createAppQueryClient()` 在每次 render 时创建。

## 默认 RuntimeConfig

组件测试不能调用 `loadRuntimeConfig()` 作为默认路径，因为它依赖 `import.meta.env` 且所有字段 required，缺值会 throw。`renderWithProviders` 使用以下 test-safe 默认值：

```ts
const defaultRuntimeConfig: RuntimeConfig = {
  apiBaseUrl: '',
  websocketUrl: '',
  mode: 'test',
  authEnabled: false,
};
```

测试可通过 `options.runtimeConfig` 覆盖单个或多个字段。覆盖只作用于当前 render 调用，不写入全局状态。

## API 草图

`renderWithProviders` 的公共 API 保持最小，只承诺 RuntimeConfig 覆盖，不承诺 QueryClient 注入。

```ts
interface RenderWithProvidersOptions {
  runtimeConfig?: Partial<RuntimeConfig>;
}

function renderWithProviders(
  ui: React.ReactElement,
  options?: RenderWithProvidersOptions,
): ReturnType<typeof render>;
```

返回值复用 RTL `render` 的返回类型。公共入口同时 re-export RTL 常用工具和 `userEvent`。

## QueryClient 边界

`AppProviders` 当前需要 `QueryClient`。为了保证测试可运行且状态隔离，helper 在内部为每次 render 调用 `createAppQueryClient()` 创建独立 QueryClient。

但本 change 不定义稳定的自定义 QueryClient 注入接口。issue 评论已说明“query client 暂时不做，接口没定”，因此 QueryClient 自定义能力应保留为后续设计点，不能在本 change 中作为公共 API 承诺。

## Playwright CT 与 RTL 的边界

Playwright Component Testing 继续作为真实浏览器 runner。RTL 负责组件级 render/query/user interaction helper。

组件测试默认使用 RTL `render`，并通过 `renderWithProviders` 接入应用 provider。Playwright `mount` fixture 保留给 CT runner 自身验证或需要 Playwright 特定挂载能力的特殊场景。两者共存但职责不同，应用组件测试不应默认用 `mount` 手写 provider。

## Setup 策略

jest-dom matcher 和 RTL cleanup 应通过 `apps/web/tests/components/setup.ts` 统一接入，并在 `playwright-ct.config.ts` 中引用，避免每个测试文件重复导入。

setup 文件必须满足：

- 只作用于 Playwright CT 项目。
- 不污染 Vitest Node unit runner。
- 不污染 Playwright E2E runner。
- 与 `playwright-ct.config.ts` 的目录和命名约定一致。

## 最小证明

使用 `PlaceholderPanel` 作为最小组件测试对象，因为它轻量、稳定且不依赖业务 API。测试应证明：

- `renderWithProviders` 可以渲染组件。
- jest-dom matcher 可用。
- 测试可从公共入口使用 RTL query。

现有 `tests/components/placeholder-panel.spec.tsx` 使用 Playwright `mount` fixture，保留作为 CT runner proof。新增 `tests/components/placeholder-panel-rtl.spec.tsx` 作为 RTL helper proof，避免把两类能力混在同一个测试里。
