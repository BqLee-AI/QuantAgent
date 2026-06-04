## Why

行业 MainAgent MVP 已经确定围绕 DeepAgents 实现 PlannerExecutor 纪律，但仓库当前只有 `packages/agent` 预留边界，缺少统一的 AgentRuntime。若后续半导体 MainAgent、API debug stream 和 Web debug chat 各自直接创建 DeepAgents 实例，会让工具授权、run context、artifact、stream 事件和审计摘要分散失控。

本 change 先收住 #284 的基础设施：业务代码只能通过统一 AgentRuntime 创建和运行 DeepAgents，并获得可测试、可流式消费的结构化 run 事件。

## What Changes

- 新增 `packages/agent` 的 AgentRuntime MVP 能力：统一解析 AgentDefinition、构造 DeepAgents runtime、注入工具、绑定 run context、产出 structured output。
- 新增通用契约：`AgentDefinition`、`SubAgentDefinition`、`ToolProfile`、`AgentRunInput`、`RunContextSnapshot`、`ArtifactRef`、`AgentRunEvent` 等 Pydantic 模型。
- 新增 run-scoped hidden context 注入机制：工具 schema 只包含模型应填写字段，`agent_run_id`、`event_id`、`trace_id`、`tool_profile_id` 等由 runtime 注入。
- 新增 MVP artifact store：默认进程内 ephemeral，实现 ID-first 传递，避免模型复制大 JSON 或文件路径。
- 新增 stream event adapter：把 DeepAgents / LangGraph 运行中的 message、todo、tool、subagent、artifact、final output 和 error 转换为稳定事件流。
- 新增 fake model / fake tool harness 和单元测试，用于在无外部模型或 secret 的情况下验证 runtime、artifact、tool adapter 和 streaming。
- 写死 DeepAgents 实现纪律：实现 PR 必须重新查阅官方 DeepAgents docs/examples、本地安装版本和本地 DeepAgents skill，并在 PR 说明记录采用的内置能力和未采用原因。

## Capabilities

### New Capabilities

- `deepagents-agent-runtime-mvp`: 定义 QuantAgent AgentRuntime MVP 的入口、DeepAgents 复用边界、工具注入、artifact、streaming、安全脱敏和测试 harness 行为。

### Modified Capabilities

- 无。

## Impact

- 主要写入范围：`packages/agent/**`、`packages/agent/tests/**`、根 `pyproject.toml` 或 workspace 配置中与 `packages/agent` 纳入测试相关的最小变更。
- 设计依据：`docs/agent/02-planner-executor-architecture.md`、`docs/agent/05-tooling-and-output-contracts.md`、`docs/agent/08-run-scoped-context-tools.md`、`docs/agent/09-agent-artifact-ownership.md`、`docs/design/05-agent-workflow-design.md`。
- 依赖与外部能力：DeepAgents / LangChain / LangGraph 当前安装版本，具体 API 签名实现前必须用官方文档、examples 和本地环境确认。
- 后续依赖：半导体 MainAgent/NVDA fixture、API debug SSE 和 Web Agent Debug Chat 都应复用本 runtime，不直接创建 DeepAgents 实例。
- 风险边界：本 change 不接真实交易、真实 broker、真实通知、生产持久化 AgentRun 表或完整长期记忆；不保存完整 chain-of-thought、完整 prompt、provider raw response、secret 或私有策略明文。
