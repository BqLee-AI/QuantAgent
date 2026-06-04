## Context

`packages/agent` 当前是 Agent workflow 能力的预留 package，`packages/agent/AGENTS.md` 已明确 AgentRuntime、ToolRegistry 和 schema 化输出是长期边界，业务代码和插件不能绕过它们创建失控 Agent 行为。`docs/design/05-agent-workflow-design.md` 同样要求 AgentRuntime 是运行 Agent 的统一入口，不让业务代码直接创建 DeepAgents 实例。

DeepAgents 官方文档确认它是基于 LangGraph 的 agent harness，提供 planning、filesystem/context management、subagent delegation、human-in-the-loop、memory 和 durable/streaming runtime 等能力。因此本 change 的核心取舍是“配置并约束 DeepAgents”，不是重写 LangGraph 状态机或自研 tool loop。

## Goals / Non-Goals

**Goals:**

- 在 `packages/agent` 提供 `AgentRuntime` 公开入口，后续 API、Worker、行业包和测试只通过它启动 Agent run。
- 使用 DeepAgents `create_deep_agent()` 和其内置 middleware 承接 planning、subagent、backend、skills、HITL/interrupt 和 streaming 能力。
- 定义通用 Pydantic 契约，支撑 AgentDefinition、SubAgentDefinition、ToolProfile、run input、artifact 引用、tool invocation 和 stream event。
- 提供 run-scoped hidden context 注入，让工具调用自动绑定 `agent_run_id`、`event_id`、`industry_id`、`agent_id`、`trace_id` 等上下文。
- 提供 ephemeral artifact store 和 ID-first 传递规则，避免模型在工具之间复制大 JSON 或任意文件路径。
- 提供 fake model/fake tool harness，保证无外部 API key 时也能测试 runtime、tool adapter、artifact 和 stream event。

**Non-Goals:**

- 不实现半导体 MainAgent prompt、NVDA fixture、Tavily 真连接、API SSE 或 Web debug 页面。
- 不接真实 broker、真实通知、真实交易或生产账户。
- 不实现生产级 AgentRun DB 表、长期 StoreBackend 记忆或 outbox/replay。
- 不保存完整 chain-of-thought、完整 prompt、完整 provider raw request/response、secret 或私有策略明文。
- 不把 API envelope、HTTP status code、SSE 协议或前端类型放入 `packages/agent`。

## Decisions

### 1. AgentRuntime 是唯一 DeepAgents 创建入口

实现应新增 `quantagent.agent.runtime.AgentRuntime`，公开最少两个入口：

- `run(request: AgentRunRequest) -> AgentRunResult`
- `run_stream(request: AgentRunRequest) -> AsyncIterator[AgentRunEvent]`

`AgentRuntime` 内部负责根据 `AgentDefinition`、`RuntimePolicy`、`ToolProfile` 和 `RunContextSnapshot` 调用 `deepagents.create_deep_agent()`。业务代码、行业包、API service 和测试 fixture 不应直接调用 `create_deep_agent()`，除非是 `packages/agent/tests` 中对 adapter 的局部单测。

备选方案是让行业包自己创建 DeepAgent，再把结果交给平台。该方案会让工具权限、provider policy、artifact、审计和 stream event 无法统一治理，因此不采用。

### 2. 目录与文件规划

目标目录：

```text
packages/agent/
  README.md
  AGENTS.md
  src/quantagent/agent/
    __init__.py
    definitions/
      __init__.py
      models.py              # AgentDefinition、SubAgentDefinition、RuntimePolicy
      loader.py              # 解析 markdown/frontmatter 或测试构造定义
    runtime/
      __init__.py
      runtime.py             # AgentRuntime 入口和 orchestration glue
      requests.py            # AgentRunRequest、AgentRunResult
      context.py             # RunContextSnapshot、hidden ToolRuntimeContext
      errors.py              # AgentRuntimeError、ToolAdapterError 等
    tools/
      __init__.py
      profiles.py            # ToolProfile、ToolBinding
      adapter.py             # 平台工具 -> LangChain/DeepAgents tool
      schemas.py             # 通用 tool invocation 摘要
    artifacts/
      __init__.py
      models.py              # ArtifactRef、ArtifactKind
      store.py               # ArtifactStore Protocol + InMemoryArtifactStore
    streaming/
      __init__.py
      events.py              # AgentRunEvent、event type 枚举和 payload
      adapter.py             # DeepAgents/LangGraph stream -> AgentRunEvent
    testing/
      __init__.py
      fake_model.py          # 无外部 provider 的测试模型或脚本化 runner
      fake_tools.py          # fake tool harness
      fixtures.py            # runtime 测试 fixture 构造
  tests/
    test_runtime_stream.py
    test_tool_adapter.py
    test_artifact_store.py
    test_definition_loader.py
```

`README.md` 必须说明 package 职责、入口、子目录、复用方式和禁止放入内容。非显然安全边界、hidden context、脱敏和“刻意不自研 DeepAgents loop”的取舍需要中文注释。

### 3. 契约模型保持通用，不为 NVDA 或财报定制

核心模型草案：

- `AgentDefinition`: `agent_id`、`version`、`name`、`description`、`system_prompt`、`tools`、`skills`、`subagents`、`provider_policy_id`、`output_schema_id`。
- `SubAgentDefinition`: `subagent_id`、`name`、`description`、`system_prompt`、`tools`、`skills`、`max_tool_calls`、`output_schema_id`。
- `ToolProfile`: `profile_id`、`tool_bindings`、`risk_policy`、`max_tool_calls`、`timeout_seconds`。
- `AgentRunRequest`: `agent_run_id`、`event_id`、`industry_id`、`agent_definition`、`run_context`、`tool_profile`、`runtime_policy`、`input_message`。
- `RunContextSnapshot`: `sections`、`safe_summary`、`artifact_refs`，只承载当前 run 已绑定的压缩上下文。
- `ToolRuntimeContext`: runtime hidden context，包含 `agent_run_id`、`event_id`、`industry_id`、`agent_id`、`subagent_id?`、`trace_id`、`tool_profile_id`。
- `ArtifactRef`: `artifact_id`、`kind`、`producer_id`、`safe_summary`、`created_from_ids`、`confidence_score?`。
- `AgentRunEvent`: `event_id`、`agent_run_id`、`type`、`seq`、`created_at`、`payload`、`safe_summary?`、`trace_id`。

所有 Pydantic model 使用 `extra="forbid"`。字段命名遵守 docs/agent 约定：artifact 引用使用 `*_artifact_id`，领域对象 ID 使用 `*_id`。

### 4. ToolAdapter 注入 hidden context

平台工具实现不应要求模型传 `agent_run_id`、`event_id`、`trace_id`、文件 path 或完整上下文 JSON。`ToolAdapter` 的职责：

- 读取工具 input Pydantic schema，生成 DeepAgents 可接收的工具。
- 在执行时注入 `ToolRuntimeContext`。
- 记录 tool started/completed/failed 事件和安全摘要。
- 对大输出调用 `ArtifactStore.put(...)`，返回 `ArtifactRef` 或包含 `artifact_id` 的小结果。
- 对错误做结构化包装，不吞异常，不暴露 traceback、secret 或内部路径。

工具 timeout、风险等级和 interrupt policy 先作为 `ToolProfile` 元数据保留；真实 Approval/Policy Gate 由后续 issue 或 `submit_action_plan` 承接。

### 5. ArtifactStore 先用 ephemeral 实现

MVP 新增 `ArtifactStore` Protocol 和 `InMemoryArtifactStore`。artifact 只保证当前进程和当前测试 run 可用，不承诺跨进程恢复。后续需要持久化时再接数据库或对象存储。

artifact store 默认保存结构化 payload 和 safe summary，但不得保存完整 prompt、完整 provider raw response、secret 或完整 CoT。实现中需要用中文注释说明该安全边界。

### 6. Streaming 采用内部稳定事件，不绑定 API SSE

`packages/agent` 只定义内部 `AgentRunEvent` async iterator，不关心 HTTP/SSE/WebSocket。后续 API issue 负责把它编码成 SSE。

事件类型最少包括：

- `run.started`
- `model.delta`
- `todo.updated`
- `tool.started`
- `tool.completed`
- `tool.failed`
- `subagent.started`
- `subagent.completed`
- `artifact.created`
- `run.output`
- `run.failed`
- `run.completed`

DeepAgents/LangGraph 原始 stream chunk 可能随版本变化，`streaming/adapter.py` 需要把当前版本的 chunk 映射到稳定事件；无法可靠映射的 chunk 只能进入 `debug` 级 safe summary，不能泄露 provider raw payload。

### 7. DeepAgents 文档查阅是实现 gate

实现 PR 必须说明：

- 查阅的官方 DeepAgents 文档 URL，例如 overview、customization/harness/backend/subagents/streaming 相关页，以及 examples repo。
- 本地安装版本和关键 API 签名确认方式。
- 哪些 DeepAgents 能力已启用：TodoList、SubAgent、backend、skills、checkpointer/HITL、streaming。
- 哪些能力刻意延后：长期 StoreBackend、生产持久化、复杂 HITL、LangSmith。

如果官方 docs 与本地版本冲突，以本地安装版本和可运行测试为准，并在 PR 中记录取舍。

## Risks / Trade-offs

- [Risk] DeepAgents stream chunk 格式随版本变化 → [Mitigation] 通过 `streaming/adapter.py` 隔离，并用 fake harness 单测固定 `AgentRunEvent` 输出。
- [Risk] 过早设计生产持久化导致实现过重 → [Mitigation] MVP 仅提供 `ArtifactStore` Protocol + in-memory 实现，后续 issue 替换 adapter。
- [Risk] 工具 adapter 变成另一个 ToolRegistry → [Mitigation] 本 issue 只做 runtime 注入和执行 wrapper，不做插件发现、权限解析或真实 registry 持久化。
- [Risk] fake harness 与真实 DeepAgents 行为偏离 → [Mitigation] 测试分两层：纯 adapter fake tests + 至少一个使用当前 DeepAgents API 的 smoke test；若外部模型不可用，使用本地 fake model 或脚本化 runnable。
- [Risk] stream 事件可能误带敏感内容 → [Mitigation] `AgentRunEvent` 只允许 safe summary 和结构化小 payload，测试覆盖 prompt/secret 不出现在 payload。

## Migration Plan

1. 将 `packages/agent` 纳入 Python workspace/test 配置，确保可以独立运行测试。
2. 新增 runtime、definitions、tools、artifacts、streaming、testing 目录和 README。
3. 先实现 Pydantic 契约、artifact store、tool adapter 和 fake harness。
4. 再接入 `create_deep_agent()` 和 stream adapter，用最小 smoke test 验证当前 DeepAgents 版本可运行。
5. 后续 issue 逐步接入半导体 MainAgent、API SSE 和 Web debug chat。

回滚策略：本 change 不迁移数据库，不影响生产 API；若实现有问题，可禁用后续调用方并保留 `packages/agent` 测试边界，不影响现有事件/插件页面。

## Open Questions

- `packages/agent` 当前是否已经在根 `pyproject.toml` workspace 中完整启用，需要实现时检查并做最小配置更新。
- 当前 DeepAgents 版本对 fake model / scripted model 的最佳测试方式需要实现前查本地安装版本和官方 examples。
- `AgentRunEvent` 是否后续同步到 `packages/contracts`，由 API/Web issue 根据跨端消费范围决定；本 change 先稳定 Python 内部契约。
