# Web Architecture Gate

本文件是 `apps/web` 在 issue、OpenSpec、implementation、PR 和 Code Review 阶段共用的目标架构门槛。它比 CR 场景细则更靠前：规划和写代码前必须先用它约束目录、职责和数据流。

现有代码只能作为迁移背景，不能自动成为新代码模板。新增或修改代码应向本文件定义的目标边界收敛；未触碰的历史债务可以记录为 residual risk 或后续 issue。

## 默认分层

`apps/web/src` 默认按职责分层：

- `app/`：bootstrap、provider、router、layout、runtime、应用级错误边界；不放业务域规则。
- `routes/`：TanStack Router 文件路由入口，只做 `createFileRoute`、loader、search、beforeLoad、redirect 和页面组合。
- `features/<domain>/`：业务域默认落点，承载 feature API、TanStack Query hooks、mutation hooks、页面业务 hooks、领域组件、局部 types 和 utils。
- `shared/`：跨业务域基础能力，例如 API transport、auth、config、errors、基础 UI 和通用 utils；不放具体业务流程。
- `styles/`：全局 token、主题和 layout fallback；不承载单页业务样式堆叠。
- `debug/`：开发态诊断入口，生产不可见，不进入正式导航。

复杂 feature 建议目录：

```text
features/<area>/<domain>/
  README.md
  api/         # endpoint class 与 API contracts
  queries/     # query keys 与 useQuery hooks
  mutations/   # useMutation hooks 与 invalidate
  hooks/       # 页面级业务 hook、筛选、表单状态
  components/  # page、panel、table、form、states 等视图组件
  types/       # UI 局部类型、表单类型、领域展示类型
  utils/       # 纯格式化、标签、能力判断等无副作用 helper
```

`README.md` 至少说明：负责什么、route 入口、公开 hook / component、子目录含义、不负责什么，以及不要继续往根目录平铺什么。

`docs/design/09-frontend-architecture-design.md` 中的 `api.ts` / `queries.ts` flat 示例只代表早期方向；新代码和重构代码以本 gate 的职责目录为准。小功能可以暂时少建子目录，但不能把不同变化原因混进同一文件。

当 Web 变更涉及新增 feature、复杂 route、目录增长、shared 能力，或同一 diff 同时改 API / query / hook / component / types / README 时，必须继续读取 `.agents/skills/references/web-file-responsibility-and-feature-structure.md`。这份文件是规划和实现阶段的规范，不是只给 CR 用。

## 文件职责矩阵

| 文件 / 目录 | 只负责 | 禁止放入 |
| --- | --- | --- |
| `routes/**` | `createFileRoute`、search/loader/beforeLoad/redirect、把 route 参数传给 feature page | `apiClient`、feature API 实例、query/mutation 实现、表格/表单主体、弹窗状态、业务格式化 |
| `features/<domain>/api/*.api.ts` | `class XxxApi extends BaseApi`、endpoint path、payload/params/response type 使用 | React state、TanStack Query、query key、toast、UI 状态、权限渲染 |
| `features/<domain>/api/*.contracts.ts` | API payload、params、response、DTO 映射边界；未来可替换 generated contracts | endpoint 实现、React hook、UI props、表单局部状态 |
| `features/<domain>/queries/*.keys.ts` | query key factory，稳定表达资源边界和筛选参数 | request 调用、组件状态、mutation invalidate |
| `features/<domain>/queries/use-*.ts` | `useQuery` 封装、调用 runtime `apis`、选择 query key | JSX、表单状态、弹窗状态、业务页面编排 |
| `features/<domain>/mutations/use-*.ts` | `useMutation` 封装、成功后 invalidate、错误透传 | JSX、页面局部状态、endpoint path 拼接 |
| `features/<domain>/hooks/use-*.ts` | 页面级业务 hook：组合 query/mutation、权限、筛选、选中项、动作 | 底层 HTTP、endpoint 定义、复杂 JSX、shared UI 实现 |
| `features/<domain>/components/page/*.tsx` | 页面组合，把业务 hook 解构后传给 panel/table/form | 底层请求、query key、DTO envelope、复杂业务规则 |
| `features/<domain>/components/**` | 展示组件、表格、表单字段、状态组件，接收稳定 props | `ApiResponse`、完整业务 DTO 透传、底层 client、跨域业务策略 |
| `features/<domain>/types/*.ts` | UI 局部类型、表单类型、展示模型、组件 props 公共类型 | endpoint 实现、hook、运行时代码 |
| `features/<domain>/utils/*.ts` | 纯函数：label、format、capability 判断、无副作用转换 | React state、请求、query cache、DOM |
| `features/<domain>/README.md` | 职责、入口、公开 API、子目录含义、禁止放什么 | 施工日志、临时 TODO、未确认设计 |

## 拆分触发阈值

同一新增或重构文件中如果同时出现以下 3 类以上，必须拆分到职责文件；如果出现在 route 或 shared UI 中，通常是 `must-fix`：

- 请求或 endpoint path：`apiClient`、`fetch`、`BaseApi`、URL 拼接。
- DTO / contracts / envelope：`ApiResponse`、payload、params、response shape、`code/data/msg/error`。
- TanStack Query：query key、`useQuery`、`useMutation`、invalidate。
- 页面局部状态：选中项、筛选草稿、抽屉/弹窗、步骤状态。
- 权限或安全：capability、403、脱敏、敏感字段。
- 格式化和派生：label、status tone、排序、筛选适配。
- 表格 / 表单主体：columns、fields、validation、drawer/modal form。
- 状态视图：loading、empty、error、permission denied、toast。

拆分不是按行数触发；一个 80 行文件同时改变 endpoint、query cache、弹窗状态和 JSX，也比一个 180 行纯展示表格更需要拆。

## 运行时与 API

API 调用链路固定为：

```text
app/runtime -> apiClient -> BaseApi -> FeatureApi -> queries/mutations -> business hooks -> view components
```

- `app/runtime` 负责创建运行时对象，包含一份 runtime-scoped `apiClient`、稳定的 `apis` 对象，以及未来 `realtime`、notifications、command bus 等运行时服务。
- 不导出模块级 `apiClient` singleton；query hook、component、route 不自己创建或持有底层 client。
- feature hook 通过 `useApis()` / `useAppRuntime()` 取稳定对象，不在 hook 内 `new XxxApi(apiClient)`。
- `BaseApi` 保持薄，只负责 `basePath`、path join、`get/post/put/patch/del/request/requestEnvelope` 和通用请求选项透传。
- `BaseApi` 不负责 list/detail/create/update/delete 资源套路、分页协议、筛选协议、启停/批量动作、query key 或 React 状态。
- `FeatureApi` 只封装 endpoint、payload、params 和 response type；普通业务域放在 `features/<domain>/api/`，Auth 这类横切能力可以放在 `shared/auth/api.ts`，但也必须遵守同一分层。
- TypeScript 类型使用 ES module type exports，不使用 `namespace` 承接业务 API types。

## Query、Mutation 与业务 Hook

- 服务端状态必须通过 TanStack Query；React state 只保存局部 UI 状态，例如选中项、抽屉开关、临时筛选输入。
- query key 必须稳定表达资源边界和筛选参数；mutation 成功后按资源边界 invalidate。
- 页面编排层使用业务 hook 命名，例如 `useXxxPage()`、`useXxxForm()`、`useXxxFilters()`。
- 推荐命名：`useModelProviderPage()`、`useProviderForm()`、`useProviderFilters()`、`useProviderList()`、`useProviderModels()`。
- 业务 hook 负责组合 query、mutation、权限、页面局部状态和动作；view component 接收解构后的字段和回调进行渲染。
- presentational component 不直接依赖 `ApiResponse`、底层 client、完整后端 DTO 或 query cache。

## 组件与目录职责

- 业务组件优先放在所属 `features/<domain>/components/`。
- `shared/ui` 只放跨域基础 UI，不含业务 API、领域权限、业务 DTO 或 feature query。
- `app/components` 只放 shell / provider / layout 级组件，不放业务域组件。
- 一个文件应只有一个主要职责和一个主要修改理由；不要把 API 调用、DTO/types、状态机、provider、hook、policy、UI 和测试 fixture 混在同一文件。
- 当目录同时出现组件、hooks、types、api、utils、tests 或文档时，按职责拆子目录，不长期平铺几十个文件。
- 中文注释用于说明非显然边界：安全、权限、审计、状态同步、并发、重试、debug 隔离、生成物边界和重要取舍。
- 不是所有小组件都需要 README；复杂 feature、共享能力、公共组件和非显然目录必须提供 README 或最小 usage note。

## 规划和 Review 口径

- Issue / OpenSpec 规划阶段必须写清目录蓝图、文件职责、runtime/API/query/hook/component 边界、失败路径、验证入口和是否需要 README / 中文注释。
- 涉及复杂 feature 或文件拆分时，Issue / OpenSpec / implementation 必须对照 `.agents/skills/references/web-file-responsibility-and-feature-structure.md` 写清目标文件和目录。
- Implementation 阶段如果发现 artifacts 没体现这些边界，应先暂停补 artifacts 或向维护者确认，不能按当前代码习惯继续堆。
- PR 阶段必须说明实现是否遵循本 gate；偏离时说明原因、风险和后续收敛点。
- Code Review 阶段只对当前 diff 中新增或扩大债务的问题给 actionable finding；未触碰历史问题列 residual risk / defer。

`must-fix` 信号：

- 新 route、component 或 hook 直接裸调 `apiClient` / `fetch` 获取业务数据。
- 在旧厚 route / provider / component 里继续追加业务请求、复杂状态、权限和弹窗流程。
- 新 shared UI 接收完整业务 DTO、`ApiResponse` 或领域权限策略。
- `BaseApi` 被加上 CRUD、分页、筛选、query key、React 状态等业务假设。
- 新增复杂 feature 无 README、无职责目录分组，或非显然安全/状态/权限边界没有中文注释。

`should-fix` 信号：

- 当前 PR 内低成本可以把新增请求移到 feature API / query。
- 业务 hook 和 view component 拆分不够清晰，但风险可控。
- props 偏宽但仍局限在单一业务域。

`defer` / `residual risk` 信号：

- 历史代码已有但当前 PR 未触碰的不规范结构。
- 需要专门迁移 issue 才能解决的大范围目录或分层问题。
