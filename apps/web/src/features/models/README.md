# models feature

`features/models` 负责 `/models` 模型供应商控制面：供应商列表、供应商详情编辑、供应商下模型管理、任务模型预设和最近调用摘要。

## Route 入口

- `apps/web/src/routes/_app/(workspace)/models/index.tsx` 只挂载 `ModelsPage`。
- 页面业务编排入口是 `hooks/use-model-provider-page.ts`。

## 公开入口

- 页面组件：`components/ModelsPage.tsx`
- 页面业务 hook：`hooks/use-model-provider-page.ts`
- API 对象：`api/model-provider.api.ts` 中的 `ModelProviderApi`
- API contracts：`api/model-provider.contracts.ts`

## 子目录职责

- `api/`：只放 `ModelProviderApi extends BaseApi` 和模型供应商 API contract 类型。
- `queries/`：只放 TanStack Query keys 和查询 hooks，通过 `useApis()` 使用 runtime 注册的稳定 API 对象。
- `mutations/`：只放 mutation hooks、query invalidation 和 provider id 本地校验。
- `hooks/`：只放页面级业务 hook，组合筛选、选中、新建态、query 和 mutation。
- `components/`：只放展示组件和页面组合组件，接收 props 渲染，不拼 endpoint、不持有 query key。
- 根目录工具文件：`errors.ts`、`provider-presets.ts` 只保留模型页局部纯逻辑。

## 不负责

- 不实现后端模型策略、ProviderManager、fallback 决策、权限绕过或交易策略判断。
- 不直接创建 `ApiClient`，不通过 `useAuth()` 暴露的底层 client 调业务 API。
- 不把 API response envelope、endpoint path、query cache 或 mutation invalidate 放进展示组件。

## 禁止继续平铺

新增模型供应商能力时不要在 feature 根目录继续新增 `api.ts`、`queries.ts`、`types.ts` 或大组件文件。按 `api/`、`queries/`、`mutations/`、`hooks/`、`components/`、`types/`、`utils/` 拆到职责目录；只有纯局部工具且不会继续增长时才可留在根目录。
