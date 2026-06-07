# Agent Audit Shared UI

`features/agent-audit` 是 `/events` 与 `/runtime` 之间共享的 Agent 审计展示边界。它只负责把已经映射好的 Agent 审计展示模型渲染为面板、详情弹窗、关键字段、结构化 JSON 和 trace refs。

## 入口

- `components/AgentStagePanel`：展示一个 subject 下的 Agent stages 摘要，并打开详情弹窗。
- `components/AgentStageDetailModal`：展示新闻标题、URL、source 摘要、content preview、stage 状态、关键字段、结构化 output JSON 和 refs。
- `components/AgentKeyFields`：展示稳定 key fields。
- `components/AgentJsonView`：展示已脱敏的 JSON-safe structured output。
- `components/AgentTraceRefs`：展示可审计引用。
- `types/agent-audit.types.ts`：定义 `AgentAuditSubject`、`AgentAuditStage`、`AgentAuditTraceRef`、`AgentAuditKeyFields` 等稳定展示模型。
- `utils/`：集中处理 label、status tone、field value 和 safe JSON 脱敏。

## 展示模型

调用方必须先在自己的 feature mapper 中把后端 DTO 转换为：

- `AgentAuditSubject`：被审计对象摘要，例如 routed news、RawEvent 或未来业务事件。
- `AgentAuditStage`：单个 Agent 处理阶段，例如 Router Agent 或未来行业 MainAgent。
- `AgentAuditKeyFields`：可扫描的关键字段摘要。
- `AgentAuditTraceRef[]`：request、trace、run、routed output 等可审计引用。

组件不接收 `ApiResponse`、ORM object、runtime 私有 DTO、完整后端 response、plugin instance 或 secret-bearing runtime object。

## 子目录职责

- `components/`：纯展示组件，只接收稳定展示模型和 UI 回调。
- `types/`：共享展示模型与 JSON-safe 值类型。
- `utils/`：无副作用格式化、状态色、脱敏和 JSON 兜底。

不要在本目录新增 API client、TanStack Query、route、provider、events/runtime mapper、业务权限判断或后端 envelope 处理。

## 安全边界

本目录默认把 `provider raw response`、prompt、CoT、secret、token、cookie、password、连接串、raw payload 和完整正文视为不可展示内容。`content_preview` 只能是调用方传入的安全预览，不等同 full article。

如果后端未返回、用户无权查看或字段已被脱敏，组件必须显示 `不可用`、`已脱敏` 或明确的 unavailable reason，不使用 mock 内容补齐。

未来新增 MainAgent 的 Markdown、message、toolcall 或 artifact 渲染能力时，仍应扩展这个共享 detail boundary，并同步更新本 README。
