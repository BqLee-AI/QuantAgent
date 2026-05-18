# AGENTS.md

## 定位

- `apps/web` 是 QuantAgent 的 React + Vite 管理台。
- 前端负责展示事件流、插件、运行时状态、设置页和人工确认等操作界面。
- 前端不负责核心策略判断、交易决策、权限绕过或后端数据真源。

## 行为约束

- API 调用优先收敛在 `src/shared/api/`，不要在页面组件里散落裸 `fetch` 或临时请求逻辑。
- 运行时配置读取优先复用 `src/shared/config/`，不要在组件中硬编码后端地址。
- 路由页面放在 `src/routes/`；应用级 provider、router 和 layout 放在 `src/app/`。
- `src/routeTree.gen.ts` 是 TanStack Router 生成文件，不手写维护业务逻辑。
- UI 文案和状态应服务管理台操作，不写营销落地页式介绍。
- 前端是运行时管理台和审批工作台，不是完整交易终端；不要新增绕过后端策略的手动交易能力。
- REST API 是业务状态真源；WebSocket 消息只触发刷新或局部短暂 patch，不能长期替代 REST 快照。
- 插件配置初版只做 schema-driven form，不允许插件注入自定义前端组件。
- Agent run、tool invocation、Skill、插件状态和审批信息只展示结构化摘要，不展示完整模型推理链。
- secret、私有策略、prompt 和敏感交易细节必须脱敏展示。

## 局部规则

- 修改 API client、错误处理或运行时配置时，同步查看已有 unit test。
- 修改路由、布局或页面交互时，优先运行对应的 unit、component 或 e2e 检查。
- 新增可复用 UI 或应用基础设施时，先检查 `src/app/` 和 `src/shared/` 的现有边界。
- 未来接入生成 client、types 或 Zod schema 时，从 `packages/contracts/generated/typescript` 消费，不手写复制契约类型。
