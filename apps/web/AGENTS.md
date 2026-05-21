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
- 公开页面保持在应用 shell 外；受保护后台页统一挂到后台路由壳下，不把鉴权、布局切换和根跳转重新堆回根路由。
- `src/routeTree.gen.ts` 是生成文件，不手写业务逻辑。
- 新增共享 UI、应用基础设施或样式前，先检查现有 `src/app/`、`src/shared/` 边界，能复用就不要平行再造。
- 新增样式优先复用现有 Tailwind token 和 utility；只有 Tailwind 明显不适合时才使用 `*.module.css`。全局样式只保留跨页面 tokens、layout 和 fallback。

## UI 与安全

- 页面文案默认使用中文；代码标识、URL path、协议字段和专有名词可保留英文。
- UI 文案服务管理台操作，不写营销落地页式介绍。
- secret、prompt、私有策略和敏感交易细节必须脱敏展示。
- Agent run、tool invocation、Skill、插件状态和审批信息只展示结构化摘要，不展示完整模型推理链。
- 插件配置优先使用 schema-driven form；没有明确契约和安全边界前，不允许插件注入自定义前端组件。

## 验证

- 修改 API client、错误处理、运行时配置时，优先跑相关 unit test。
- 修改路由、layout、页面交互时，优先跑对应的 unit、component 或 e2e 检查。
- 路由结构变更后，先用现有 TanStack 生成流程刷新 `src/routeTree.gen.ts`，再跑构建。
- 如果验证缺依赖或环境不可用，最终说明必须写清楚未验证项和原因。
- 新增本地调试页面、页面状态预览、runtime config 可视化、route playground 或类似开发态入口时，优先收口到 `/debug` 工作台；不要继续在业务 route 上增加临时 query 参数、按钮或局部 hack，除非已有 issue、OpenSpec 或维护者评论明确要求它作为正式功能保留。
