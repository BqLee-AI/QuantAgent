# Web 文件职责与 Feature 结构

本文件是 `apps/web` 在规划、OpenSpec、实现、PR 和 Code Review 阶段共用的文件职责规范。它不是一般“代码风格”检查，而是为了让 AI 和维护者能定向阅读、定向修改，避免一次变更把请求、DTO、query cache、状态、权限和 UI 全塞进同一个上下文。

## 适用范围

出现以下信号时，写 issue、OpenSpec、实现计划、代码或 review 都必须加载本文件：

- 新增或重构 `src/features/**`、`src/routes/**`、`src/shared/**`、`src/app/**` 下的复杂能力。
- 新 route 中出现业务请求、表格、表单、弹窗、权限动作或复杂状态。
- feature 根目录继续新增多种职责文件，或一个目录里混有组件、hooks、types、api、utils、tests。
- shared UI / shared capability 接收业务 DTO、业务权限、feature query 或 API response。
- diff 同时修改 API、types、query、component、route、README 或测试，且职责边界不清。

只改文案、简单样式或旧文件内单一展示逻辑时，不强制加载；看到历史债务可以列 residual risk 或后续 issue。

## 目标结构

复杂 feature 默认使用职责目录：

```text
features/<area>/<domain>/
  README.md
  api/
    <domain>.api.ts
    <domain>.contracts.ts
  queries/
    <domain>.keys.ts
    use-<resource>-list.ts
    use-<resource>-detail.ts
  mutations/
    use-create-<resource>.ts
    use-update-<resource>.ts
  hooks/
    use-<domain>-page.ts
    use-<domain>-filters.ts
    use-<domain>-form.ts
  components/
    page/
    <resource>-list/
    <resource>-form/
    states/
  types/
    <resource>.types.ts
    <resource>-form.types.ts
  utils/
    <resource>-label.ts
    <resource>-capability.ts
```

小功能可以少建目录，但必须保持“一个文件一个主要职责”。如果本 PR 已经新增请求、query、状态和视图，不能再用“小功能”作为继续平铺的理由。

## 规划与实现步骤

1. 先列出新增和修改文件，按 route、api、contracts、query keys、queries、mutations、hooks、components、types、utils、README 归类。
2. 对每个文件问：它是否只有一个主要修改理由？如果不是，指出应该拆到哪些目标文件。
3. 检查 route 是否只做入口 glue；业务编排 hook 的实现不能放在 route 文件里。
4. 检查 feature API 是否只封装 endpoint；query key、mutation invalidate、toast、React state 不能放进去。
5. 检查业务 hook 是否只组合状态和动作；底层 HTTP、DTO envelope 和复杂 JSX 不能放进去。
6. 检查 components 是否只渲染 props；完整 API response、底层 client、跨域权限策略不能透传。
7. 检查 README / usage note 是否说明职责、入口、公开 hook/component、子目录含义和禁止放什么。

OpenSpec `design.md` / `tasks.md` 必须体现这些目录和文件职责；如果 artifacts 没写清，不进入实现。

## Must-fix / must-plan

- 新 route 内同时新增业务请求、服务端列表状态、表格/表单主体或弹窗状态。
- 新增复杂 feature 只有一个大文件或根目录平铺，并且混入请求、DTO、query、业务 hook、组件和状态视图。
- shared UI 接收完整业务 DTO、`ApiResponse`、领域权限策略或 feature query。
- feature API 文件中实现 query key、`useQuery` / `useMutation`、toast、React state 或页面动作。
- query / mutation hook 内直接 `new XxxApi(apiClient)`，而不是通过 runtime `useApis()` 获取稳定 API 对象。
- 删除或跳过复杂 feature README，导致公开入口、子目录职责和禁止放入内容不可判读。
- 非显然安全、权限、状态同步、debug 隔离或生成物边界没有中文注释。

## Should-fix / should-plan

- feature 根目录新增少量平铺文件，但当前 PR 可以低成本迁到 `api/`、`queries/`、`hooks/`、`components/`。
- 一个组件同时做格式化和展示，但仍局限在单一业务域、风险可控。
- props 偏宽但未透传完整 API response；建议收敛到展示所需字段。
- README 缺少公开入口或“不负责什么”，但目录职责仍大致可读。

## Defer / residual risk

- 旧厚 route 只改文案、样式或单个静态 label；不要求本 PR 顺手重构。
- 历史 feature 目录已经平铺，但本 PR 未新增复杂职责。
- 需要跨多个页面迁移的目录重组，应开后续 issue，不作为当前小 PR 的 inline finding。

## Good example：模型供应商配置与模型列表

```text
features/settings/model-providers/
  README.md
  api/
    model-provider.api.ts
    model-provider.contracts.ts
  queries/
    model-provider.keys.ts
    use-provider-list.ts
    use-provider-detail.ts
    use-provider-models.ts
  mutations/
    use-create-provider.ts
    use-update-provider.ts
    use-delete-provider.ts
    use-refresh-provider-models.ts
    use-toggle-provider-enabled.ts
  hooks/
    use-model-provider-page.ts
    use-provider-form.ts
    use-provider-filters.ts
  components/
    page/
      model-provider-page.tsx
    provider-list/
      provider-list-panel.tsx
      provider-list-toolbar.tsx
      provider-list-table.tsx
    provider-form/
      provider-form-drawer.tsx
      provider-form-fields.tsx
    model-list/
      provider-model-list-panel.tsx
      provider-model-table.tsx
    states/
      provider-empty-state.tsx
      provider-error-state.tsx
  types/
    provider.types.ts
    model.types.ts
    provider-form.types.ts
  utils/
    provider-label.ts
    provider-capability.ts
```

```ts
// api/model-provider.api.ts
export class ModelProviderApi extends BaseApi {
  constructor(apiClient: ApiClient) {
    super(apiClient, { basePath: "/settings/model-providers" });
  }

  listProviders(params: ProviderListParams) {
    return this.get<ProviderListResponse>("/", { params });
  }
}

// queries/use-provider-list.ts
export function useProviderList(params: ProviderListParams) {
  const { modelProviders } = useApis();

  return useQuery({
    queryKey: modelProviderKeys.list(params),
    queryFn: () => modelProviders.listProviders(params),
  });
}

// hooks/use-model-provider-page.ts
export function useModelProviderPage() {
  const filters = useProviderFilters();
  const providerList = useProviderList(filters.params);
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null);
  const providerModels = useProviderModels(selectedProviderId);
  const refreshModels = useRefreshProviderModels();

  // 中文注释：页面级 hook 只组织局部状态和动作，view 不直接拼 query / mutation。
  return {
    filters,
    providerList,
    providerModels,
    selectedProviderId,
    setSelectedProviderId,
    refreshModels,
  };
}
```

## Bad example

```tsx
// routes/settings/model-providers.tsx
export const Route = createFileRoute("/_app/settings/model-providers")({
  component: function ModelProvidersRoute() {
    const [providers, setProviders] = useState<ProviderDto[]>([]);
    const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null);
    const [formOpen, setFormOpen] = useState(false);

    useEffect(() => {
      apiClient.get<ApiResponse<ProviderListResponse>>("/settings/model-providers").then((response) => {
        if (response.code === 0) setProviders(response.data.items);
      });
    }, []);

    return <ProviderTable providers={providers} onCreate={() => setFormOpen(true)} />;
  },
});
```

问题：route 同时承担请求、envelope、服务端状态、选中状态、弹窗状态和表格视图，应拆到 feature API、queries、business hook 和 components。

## 验证建议

- 文档 / 结构规则：`git diff --check`
- Web feature 实现：至少跑 `bun run --cwd apps/web build`，按风险补 unit / component test。
