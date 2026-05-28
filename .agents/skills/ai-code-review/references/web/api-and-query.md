# Web API 与 TanStack Query 审查

本文件用于审查 `apps/web` 中 API 调用、服务端状态和错误可观测相关变更。

## 适用范围

触发信号：

- 修改 `src/shared/api/**`、`src/features/**/api.ts`、`src/features/**/queries.ts`、`src/features/**/mutations.ts`。
- route、component、hook 中出现 `apiClient`、`fetch`、`axios`、`ApiResponse`、`code/data/msg/error`。
- 修改 query key、mutation invalidate、request id / trace id 展示、错误 toast 或 `ApiError`。

## 目标规范

- API 调用链路固定为：`app/runtime -> apiClient -> BaseApi -> FeatureApi -> query/mutation/hook -> UI`。
- `shared/api` 只负责底层 client、envelope unwrap、错误类型、request id / trace id、CSRF 和通用请求能力。
- `shared/api/client.ts` 只定义 `createApiClient` 和 `ApiClient` 的 HTTP 请求实现；不导出默认 singleton，不知道 auth、plugins、events、approval 等业务 endpoint。
- `shared/api/base-api.ts` 提供单层 `BaseApi` 基类，只负责 `basePath`、endpoint path 拼接和受保护的 `get/post/put/patch/del/requestEnvelope` helper；多 `baseURL` 用多个 client 实例，不做复杂继承树。
- `app/runtime` 负责创建运行时级 `apiClient`、`apis` 和未来 `realtime` 等服务；页面和 query hook 默认通过 `useApis()` 或 `useAppRuntime()` 取用，不从 `useAuth()` 暴露业务 API，也不在 hook 内手动 `new XxxApi(apiClient)`。
- 业务 endpoint 默认进入 `features/<domain>/api.ts`，服务端状态进入 `features/<domain>/queries.ts` / `mutations.ts`。
- feature `api.ts` 只封装 endpoint 和 DTO，不放 React state、TanStack Query cache、view state 或 UI；推荐导出 `class XxxApi extends BaseApi`。
- Auth 是横切能力，可以放在 `shared/auth/api.ts`，但仍必须走 `class AuthApi extends BaseApi`，不能复制旧 `context.tsx` 包办请求、状态和 React 生命周期的模式。
- route 和 presentational component 不直接调用 `apiClient.get/post`、裸 `fetch` 或 `axios`。
- 页面不手写后端 envelope 解析，不直接判断 `response.code` 或拼装 `error.request_id`。
- 服务端状态使用 TanStack Query；React state 只保存局部 UI 状态。
- mutation 成功后按资源边界 invalidate；不要靠手改缓存掩盖服务端状态不一致。
- 跨端字段或 API shape 变化要判断是否需要 contracts / OpenAPI / schema 跟进。

不要使用 TypeScript `namespace` 管理 API types；使用 ES module type exports，未来方便替换为 generated contracts。

## 审查步骤

1. 找出 diff 中所有请求入口：`apiClient`、`fetch`、`axios`、`requestEnvelope`、query/mutation hook。
2. 判断调用所在层：`shared/api`、feature API、feature query、route、component、test fixture。
3. 检查 envelope 和错误处理是否只在 shared client 层解包，业务层是否接收已归一化数据或 `ApiError`。
4. 检查 query key 是否稳定，是否包含资源边界和筛选参数。
5. 检查 mutation 成功、失败、权限不足、网络错误是否有可排查反馈。
6. 检查文件职责是否单一：runtime 容器、client 配置、dedupe、envelope、errors、BaseApi、FeatureApi、query hook 和 UI 是否分开。

## Must-fix

- 新增 route/component 直接裸调 `apiClient` 或 `fetch` 获取业务数据。
- 新增页面手写 `response.code === 0`、`response.data`、`response.msg` 等 envelope 解析。
- 把 REST 快照长期复制进 React state / Zustand，并绕过 TanStack Query 刷新机制。
- mutation 后只修改本地 UI 状态，不 invalidate 相关资源且无明确理由。
- 错误 UI 吞掉 `requestId` / `traceId`，导致后端错误不可排查。
- 新增代码把 `apiClient`、runtime 初始化、业务 endpoint、React provider、session state 和 UI feedback 混进同一文件。
- 在 query hook、component 或 route 内直接 `new XxxApi(apiClient)`，而不是通过 runtime 暴露稳定 `apis` 对象复用。

## Should-fix

- query key 命名过于随意，但当前不会造成缓存碰撞。
- feature API 和 query hook 拆分不充分，但可以在当前 PR 内低成本收敛。
- `requestEnvelope` 用于业务页面但只是为了取 `msg`；应改由错误/成功状态模型承接。

## 常见误判

- `src/shared/api/client.ts` 内部允许使用 axios/fetch 语义；这是底层 client。
- 测试中的 mock envelope 可以构造 `code/data/msg/error`。
- 只改旧页面文案时，不要求顺手把历史裸请求全部迁走。
- 开发态 debug 页面可以调用诊断 API，但不能成为正式业务页面模板。

## Good example

```ts
// features/plugins/api.ts
export class PluginsApi extends BaseApi {
  constructor(apiClient: ApiClient) {
    super(apiClient, { basePath: "/plugins" });
  }

  list(params: PluginListParams) {
    return this.get<PluginListResponse>("/", { params });
  }
}

// app/runtime/runtime.factory.ts
export function createAppRuntime(options: CreateAppRuntimeOptions): AppRuntime {
  const apiClient = createApiClient({
    baseURL: options.config.apiBaseUrl,
    getCsrfToken: options.auth.getCsrfToken,
    onUnauthorized: options.auth.handleUnauthorized,
  });

  return {
    apiClient,
    apis: {
      auth: new AuthApi(apiClient),
      plugins: new PluginsApi(apiClient),
    },
    realtime: {
      client: null,
      status: "disabled",
    },
  };
}

// features/plugins/queries.ts
export function usePluginList(params: PluginListParams) {
  const { plugins } = useApis();

  return useQuery({
    queryKey: pluginQueryKeys.list(params),
    queryFn: () => plugins.list(params),
  });
}
```

Auth 作为横切能力也遵守同一分层：

```ts
// shared/auth/api.ts
export class AuthApi extends BaseApi {
  constructor(apiClient: ApiClient) {
    super(apiClient, { basePath: "/auth" });
  }

  loginWithPassword(payload: LoginPayload) {
    return this.post<LoginPayload, AuthenticatedActor>("/login", payload, {
      skipCsrf: true,
    });
  }
}
```

## Bad example

```tsx
// routes/plugins/index.tsx
useEffect(() => {
  apiClient.get<ApiResponse<PluginListResponse>>("/plugins").then((response) => {
    if (response.code === 0) setRows(response.data?.items ?? []);
  });
}, [apiClient]);
```

问题：route 直接请求业务 API、手写 envelope、复制服务端状态。

```tsx
// features/plugins/queries.ts
export function usePluginList() {
  const { apiClient } = useAuth();
  const pluginsApi = new PluginsApi(apiClient);

  return useQuery({
    queryKey: ["plugins"],
    queryFn: () => pluginsApi.list(),
  });
}
```

问题：业务 hook 自己 new feature API，运行时对象不稳定，也把 API 装配责任散回 feature 层。

## 验证建议

- API client、错误处理、runtime config：`bun run --cwd apps/web test:unit`
- 路由或页面组合：`bun run --cwd apps/web build`
- 复杂交互：按风险选择 component test 或 e2e。
