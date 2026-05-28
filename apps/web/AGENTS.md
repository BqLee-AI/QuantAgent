# AGENTS.md

## 定位

- 本文件是 `apps/web` 的下层规则，只补充或收紧根目录 `AGENTS.md`，不能放宽上层规则。
- 只记录 `apps/web` 范围内长期有效、可执行、能减少 AI 误判的约束，不写临时方案、施工计划或实现说明。
- `apps/web` 是 QuantAgent 的 React + Vite 管理台。

## 边界

- 前端只负责运行时管理、展示、审批、配置和操作入口。
- 前端不能实现核心策略判断、交易决策、权限绕过、后端数据真源或插件运行逻辑。
- REST API 是业务状态真源；WebSocket 只用于状态提醒或短期 UI patch，不能长期替代 REST 快照。

## 目录与代码

- API 调用收敛到 `src/shared/api/`；不要在页面组件里散落裸 `fetch` 或临时请求逻辑。
- 运行时配置收敛到 `src/shared/config/`；不要在组件中硬编码后端地址或部署参数。
- 应用级 provider、router、layout 放在 `src/app/`。
- 路由页面放在 `src/routes/`，遵守 TanStack Router 文件路由约定。
- route 文件只负责页面入口、loader、search params 和页面组合；业务 query、mutation、组件和局部类型进入 `src/features/<domain>/`，跨模块基础 UI/API/auth/config/errors/utils 进入 `src/shared/`。
- 公开页面保持在应用 shell 外；受保护后台页统一挂到后台路由壳下，不把鉴权、布局切换和根跳转重新堆回根路由。
- `src/routeTree.gen.ts` 是生成文件，不手写业务逻辑。
- 新增共享 UI、应用基础设施或样式前，先检查现有 `src/app/`、`src/shared/` 边界，能复用就不要平行再造。
- 新增样式优先复用现有 Tailwind token 和 utility；只有 Tailwind 明显不适合时才使用 `*.module.css`。全局样式只保留跨页面 tokens、layout 和 fallback。
- 服务端状态使用 TanStack Query；页面不得把 REST 快照长期复制进 React state 或绕过 shared API client 手写 envelope/error 处理。
- `src/features/<domain>/`、`src/shared/<capability>/` 和 `src/app/` 下的目录不能长期扁平堆文件；当一个目录同时承载组件、hooks、types、api、utils 或文档时，必须拆成子目录或职责文件组，避免几十个文件平铺难以定位。
- 共享能力、复杂 feature 和公共组件目录必须补 `README.md` 或最小 usage note，说明该目录负责什么、公开入口是什么、不要往里继续放什么。

## 组件与样式

- HeroUI v3 是基础组件库；Button、Input、Modal、Table、Tabs、Tooltip、Toast、Menu 等基础交互优先使用 HeroUI，不要随手自造同类组件。
- TailwindCSS 是默认样式表达；优先使用现有 token、utility 和 `tailwind-merge` 组合样式，避免为普通布局、间距、颜色和状态单独写 CSS。
- 页面出现可复用区块、复杂状态、表单、表格、timeline、risk panel、权限状态、错误/空/加载态时，必须拆成命名组件和必要 hooks，不能把所有 JSX、请求和状态堆在 route 文件里。
- 业务组件优先放在对应 `src/features/<domain>/components/`；只有跨两个以上业务域复用且不含业务规则的组件才进入 `src/shared/ui/`。
- 组件目录增长时，必须继续按 `components/`、`hooks/`、`view-models/`、`types/` 等职责拆分；不要在单个目录下无序平铺一批命名随意的组件文件。
- 新增 UI 必须覆盖 loading、empty、error、permission denied、sensitive masked 等与本功能相关的状态；权限不足和后端错误应显示可排查的 request id。
- 管理台 UI 应保持密度、可扫描性和操作反馈，不写营销落地页式 hero、装饰性大卡片或与运行时管理无关的介绍文案。

## UI 与安全

- 页面文案默认使用中文；代码标识、URL path、协议字段和专有名词可保留英文。
- UI 文案服务管理台操作，不写营销落地页式介绍。
- 非显然实现、边界条件和架构取舍优先写中文注释，尤其是 auth、API、权限、状态同步、debug 隔离和生成物边界。
- secret、prompt、私有策略和敏感交易细节必须脱敏展示。
- Agent run、tool invocation、Skill、插件状态和审批信息只展示结构化摘要，不展示完整模型推理链。
- 插件配置优先使用 schema-driven form；没有明确契约和安全边界前，不允许插件注入自定义前端组件。

## 验证

- 修改 API client、错误处理、运行时配置时，优先跑相关 unit test。
- 修改路由、layout、页面交互时，优先跑对应的 unit、component 或 e2e 检查。
- 路由结构变更后，先用现有 TanStack 生成流程刷新 `src/routeTree.gen.ts`，再跑构建。
- 如果验证缺依赖或环境不可用，最终说明必须写清楚未验证项和原因。
- 新增本地调试页面、页面状态预览、runtime config 可视化、route playground 或类似开发态入口时，优先收口到 `/debug` 工作台；不要继续在业务 route 上增加临时 query 参数、按钮或局部 hack，除非已有 issue、OpenSpec 或维护者评论明确要求它作为正式功能保留。
