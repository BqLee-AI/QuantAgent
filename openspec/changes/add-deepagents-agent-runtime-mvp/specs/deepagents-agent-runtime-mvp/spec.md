## ADDED Requirements

### Requirement: AgentRuntime 统一入口
系统 SHALL 在 `packages/agent` 提供统一 `AgentRuntime`，业务代码、行业包、API service 和 Worker 必须通过该入口运行 DeepAgents，不得绕过 runtime 直接创建 DeepAgents 实例。

#### Scenario: 调用方通过 runtime 启动 run
- **WHEN** 调用方传入 `AgentRunRequest`
- **THEN** `AgentRuntime` 基于请求中的 `AgentDefinition`、`RunContextSnapshot`、`ToolProfile` 和 `RuntimePolicy` 创建并运行 DeepAgents
- **AND** 调用方获得结构化 `AgentRunResult` 或 `AgentRunEvent` 流

#### Scenario: 行业包不直接创建 DeepAgents
- **WHEN** 行业包提供 MainAgent 或 SubAgent 资产
- **THEN** 行业包只声明 definition、prompt、skills、tool profile 和 fixture
- **AND** 行业包不得直接调用 `create_deep_agent()` 绕过 `AgentRuntime`

### Requirement: DeepAgents 能力复用边界
`AgentRuntime` SHALL 复用 DeepAgents 的 planning、subagent、backend、skills、HITL/interrupt 和 streaming 能力，不得自研替代 DeepAgents tool loop、todo planner 或 subagent dispatcher。

#### Scenario: Runtime 创建 DeepAgents harness
- **WHEN** runtime 构造一次 Agent run
- **THEN** runtime 使用当前安装版本支持的 `create_deep_agent()` 或等价官方入口
- **AND** runtime 将工具、SubAgent、backend、skills、checkpointer/interrupt policy 作为配置注入

#### Scenario: 实现 PR 记录文档依据
- **WHEN** 该 change 进入实现 PR
- **THEN** PR 说明列出已查阅的官方 DeepAgents docs/examples、本地安装版本和关键 API 签名确认方式
- **AND** PR 说明解释哪些 DeepAgents 内置能力被启用，哪些能力延后以及原因

### Requirement: 通用 Definition 与 Run 契约
系统 SHALL 使用通用 Pydantic 契约描述 AgentDefinition、SubAgentDefinition、ToolProfile、AgentRunRequest、RunContextSnapshot、ArtifactRef 和 AgentRunEvent，不得为 NVDA、财报或单一行业事件定制字段。

#### Scenario: 契约拒绝未知字段
- **WHEN** 调用方构造 runtime 契约对象并传入未知字段
- **THEN** Pydantic 校验拒绝该输入
- **AND** 错误摘要不暴露 secret、prompt 原文或内部路径

#### Scenario: Artifact 字段命名保持 ID-first
- **WHEN** 工具或 Agent 需要引用大产物
- **THEN** 契约使用 `*_artifact_id` 或 `ArtifactRef.artifact_id` 传递引用
- **AND** 领域对象 ID 使用 `*_id`，不得让同一字段混用 artifact namespace 和 domain namespace

### Requirement: ToolAdapter 注入 run-scoped hidden context
系统 SHALL 通过 ToolAdapter 将平台工具包装为 DeepAgents 可调用工具，并在执行时注入 run-scoped hidden context；模型输入 schema 不要求填写 `agent_run_id`、`event_id`、`trace_id`、`tool_profile_id` 或任意本地文件路径。

#### Scenario: 工具执行自动获得上下文
- **WHEN** DeepAgents 调用一个已包装工具
- **THEN** ToolAdapter 将模型输入与 `ToolRuntimeContext` 合并后调用平台工具
- **AND** 工具调用审计摘要包含 run、event、agent、tool profile 和 trace 关联信息

#### Scenario: 工具失败被结构化处理
- **WHEN** 工具执行失败或超时
- **THEN** runtime 产出 `tool.failed` 或等价失败事件
- **AND** 失败 payload 只包含脱敏错误摘要，不包含 traceback、secret、完整 prompt 或内部绝对路径

### Requirement: Run-scoped Artifact Store
系统 SHALL 提供 run-scoped artifact store 的 MVP 实现，用于保存上下文、工具结果、SubAgent 报告和最终输出的结构化产物，并返回可跨工具/Agent 传递的 `ArtifactRef`。

#### Scenario: 大工具结果保存为 artifact
- **WHEN** 工具结果超过 runtime 的直接返回预算或需要被后续工具引用
- **THEN** runtime 将结果保存为 artifact
- **AND** 工具返回值只包含 `artifact_id`、`kind`、`safe_summary` 等小引用字段

#### Scenario: Artifact 不保存敏感原文
- **WHEN** artifact store 保存 payload
- **THEN** store 不保存完整 chain-of-thought、secret、完整 provider raw response 或私有策略明文
- **AND** 可展示摘要必须来自 `safe_summary`

### Requirement: AgentRunEvent 流式输出
系统 SHALL 提供 `run_stream` 或等价 async streaming 入口，将 DeepAgents / LangGraph 运行过程转换为稳定的 `AgentRunEvent` 流。

#### Scenario: Run 输出关键生命周期事件
- **WHEN** 一次 Agent run 正常执行
- **THEN** stream 至少包含 `run.started`、中间过程事件和 `run.completed`
- **AND** 中间过程事件能够表达模型增量、todo、tool、subagent、artifact 或最终输出中的至少一种

#### Scenario: Run 失败输出失败事件
- **WHEN** Agent run 因工具错误、输出校验错误、timeout 或 runtime 错误失败
- **THEN** stream 产出 `run.failed` 或等价失败事件
- **AND** 失败事件包含可审计的脱敏错误摘要和 trace 关联信息

### Requirement: 无外部依赖测试 Harness
系统 SHALL 提供 fake model / fake tool harness，使 AgentRuntime、ToolAdapter、ArtifactStore 和 stream adapter 在没有外部 LLM provider、Tavily key、broker 或账户 secret 的情况下可测试。

#### Scenario: Fake run 可验证 stream 和 artifact
- **WHEN** 测试使用 fake harness 启动一次 runtime run
- **THEN** 测试能够断言 stream event 顺序、工具 hidden context、artifact 引用和 final output
- **AND** 测试不依赖外部网络、真实模型 API key 或真实交易账户

#### Scenario: Safety regression test
- **WHEN** fake 工具或 fake context 包含模拟 secret、prompt 或私有策略片段
- **THEN** stream event、safe summary 和 artifact ref 不包含这些敏感原文
- **AND** 测试失败时能定位是哪类输出边界泄露
