# 05. Agent Workflow 设计

## 文档状态

**状态**：草案 v0.2  
**范围**：AgentRuntime、DeepAgents 工作流、Agent 定义、插槽设计、Tool Registry、Provider 管理、插件自定义工具、运行状态和评估  
**当前约定**：Agent / Workflow 框架使用 DeepAgents，底层尽量复用 LangGraph / LangChain / LiteLLM 等成熟开源能力  
**不包含**：具体 prompt 内容、具体行业 Agent 规则、模型供应商账号配置、生产级评估平台

## 设计原则

- 不自研完整 Agent 框架，优先复用 DeepAgents、LangGraph、LangChain 和 LiteLLM。
- 核心系统负责 AgentRuntime、registry、权限、上下文、事件和插件协作。
- 行业包可以提供 Agent 定义、工具、评分规则和领域上下文，但不能绕过核心 Decision。
- Agent 的输入输出必须 schema 化，避免每个行业包返回任意自然语言。
- Provider 管理独立于 Agent 定义，Agent 不直接绑定某个模型供应商。
- 工具必须统一注册和治理，插件自定义工具不能直接暴露为无限权限执行能力。
- Agent 定义确认使用 Markdown + frontmatter。
- ProviderManager 初版确认使用 LiteLLM SDK，后续再评估 LiteLLM Proxy。
- 工具统一走 ToolRegistry；工具本身也按插件式能力治理。
- Agent 的所有外部行动都通过 tool 调用完成，包括事件分发、subagent 调用、证据检索、通知、盯盘和交易执行请求。

## 开源能力复用建议

| 能力 | 建议复用 | 用途 |
| --- | --- | --- |
| Agent harness | DeepAgents | planning、subagent、filesystem、memory、HITL、long-running task |
| Workflow runtime | LangGraph | durable execution、streaming、checkpoint、interrupt |
| Tool abstraction | LangChain tools | 标准化工具定义和调用 |
| Provider gateway | LiteLLM | 多供应商接入、fallback、routing、成本统计 |
| Schema validation | Pydantic / JSON Schema | Agent 输入输出、工具参数、插件定义 |
| Frontmatter 解析 | python-frontmatter 或 YAML parser | 从 agent 定义文件读取 metadata |
| Retry / timeout | tenacity + runtime timeout policy | 外部工具和 provider 调用可靠性 |
| Tracing / observability | LangSmith 或 OpenTelemetry | Agent 调试、调用链追踪和评估 |

## 总体架构

```text
Event
  -> AgentRuntime
  -> AgentDefinitionRegistry
  -> ToolRegistry
  -> ProviderManager
  -> DeepAgent / LangGraph Runtime
  -> Structured Output
  -> Scoring / Decision
```

## AgentRuntime

AgentRuntime 是系统运行 Agent 的统一入口，不让业务代码直接创建 DeepAgents 实例。

### 职责

- 根据事件和行业包选择 AgentDefinition。
- 加载 Agent 的 system prompt、工具、slots、provider policy。
- 从 ToolRegistry 获取可用工具。
- 从 ProviderManager 获取模型。
- 创建 DeepAgents runtime。
- 控制超时、重试、中断、人工确认和错误处理。
- 输出结构化结果。
- 记录运行状态和审计摘要。

### 推荐方案

采用核心自研轻量 `AgentRuntime`，但内部不自研 Agent loop，而是调用 DeepAgents / LangGraph。

原因：

- DeepAgents 已提供 planning、subagent、filesystem、memory、HITL 等 Agent 基础能力。
- 我们仍然需要自己的业务边界：插件权限、行业包配置、Decision 阻断、审计、provider 策略。
- 如果让插件直接创建 Agent，会导致工具权限、模型选择、审计和错误处理失控。

### 初版边界

- 支持单事件触发单个或多个行业 Agent。
- 支持行业 Agent 调用插件工具。
- 支持结构化输出。
- 支持运行状态记录。
- 暂不实现复杂多 Agent 自主协商协议。

## Agent 定义文件

Agent 定义采用 Markdown + frontmatter。

```text
agent.md
```

示例：

```markdown
---
id: quantagent.official.agent.oil_supply_analyst
name: Oil Supply Analyst
type: industry_analyst
version: 0.1.0
provider_policy: balanced
tools:
  - quantagent.official.source.rss.search
  - quantagent.official.market.us_futures.quote
skills:
  - skills/oil-market-analysis
  - skills/geopolitical-risk
slots:
  - event
  - industry_context
  - evidence
output_schema: industry_analysis.schema.json
---

You are an oil supply-demand analyst...
```

### 设计说明

frontmatter 管理 Agent 元数据，正文保存 Agent 指令。

原因：

- Agent 指令需要给人读和编辑，Markdown 比纯 JSON/YAML 更自然。
- frontmatter 适合声明 id、version、tools、skills、slots、provider_policy、output_schema 等结构化信息。
- 行业包可以随包分发自己的 Agent 定义。
- 核心系统可以解析 frontmatter 并做权限和 schema 校验。

### 约束

- Agent 定义必须有 `id`、`version`、`type`、`tools`、`skills`、`slots`、`output_schema`。
- Agent 定义中的 tools 只是声明需求，最终可用工具必须由 ToolRegistry 授权。
- Agent 定义中的 skills 是标准 Skill 包引用，必须通过 Skill Registry 解析和授权，AgentRuntime 再按需读取对应 `SKILL.md` 和资源。
- Agent 定义不能直接写 API key、账户信息或敏感配置。
- Agent 定义版本需要随插件版本记录。

### Agent 绑定 Skill

不同 Agent 可以绑定不同 Skill。

示例：

```yaml
skills:
  - skills/oil-market-analysis
  - skills/geopolitical-risk
```

规则：

- skill 路径指向标准 Skill 包目录，而不是单个 Markdown 文件。
- Skill 包必须包含 `SKILL.md`。
- Skill 必须先进入 Skill Registry，支持官方通用 Skill、行业包内置 Skill、runtime/private Skill。
- AgentRuntime 先读取 `SKILL.md` 的 frontmatter 和主体说明。
- `references/`、`assets/`、`scripts/` 只在 Agent 任务需要时按需加载或执行。
- Agent 只能加载 Skill Registry 中已注册且已授权的 Skill。

## 插槽设计

Slots 用来定义 Agent 运行时需要注入的上下文。

### 初版核心 slots

| Slot | 内容 | 来源 |
| --- | --- | --- |
| `event` | 标准化事件 | Event store |
| `raw_event` | 原始事件摘要 | RawEvent store |
| `industry_context` | 行业包上下文 | Industry Plugin |
| `skills` | Agent 绑定的 Skill 内容 | AgentDefinition / Skill package |
| `plugin_config` | 插件非敏感配置 | Plugin Config |
| `tools` | 授权工具列表 | ToolRegistry |
| `evidence` | 已收集证据 | Source / Tool results |
| `risk_policy` | 风控约束 | Core policy |
| `output_schema` | 输出结构 | Contracts / Plugin |

### 设计说明

采用显式 slots，不让 Agent 自由读取全局上下文。

原因：

- 可以控制上下文大小。
- 可以避免插件越权读取不该看的配置。
- 可以让 Agent 运行结果更可复现。
- 后续 UI 可以展示每次 Agent 运行使用了哪些上下文。

## Tool Registry

Tool Registry 是 Agent 工具的统一注册中心。

### 工具来源

- 核心系统内置工具。
- Source Plugin 暴露的查询工具。
- Industry Plugin 暴露的领域工具。
- Strategy Plugin 暴露的策略工具。
- Notification / broker 插件暴露的受控工具。

## Tool-first Agent 行动模型

Agent 不直接调用系统内部服务，也不直接写数据库或执行交易。Agent 的所有外部行动都表达为 tool invocation。

典型链路：

```text
RouterAgent
  -> tool: dispatch_to_industry_agent
  -> Industry Main Agent
  -> tool: call_subagent
  -> tool: read_source / query_market / read_shipping_data
  -> tool: run_debate
  -> tool: generate_trade_plan
  -> tool: notify_user
  -> tool: request_monitoring
  -> tool: request_broker_action
```

这样做的原因：

- 所有行动都能审计。
- 所有工具都能做权限控制、schema 校验、限流、超时和重试。
- 行业包可以扩展能力，但不能绕过 ToolRegistry。
- 高风险行为可以通过 Decision / Policy Gate 统一拦截。

### 工具分类

| 类型 | 示例 | 说明 |
| --- | --- | --- |
| routing tool | `dispatch_to_industry_agent` | 将事件派发给候选行业主 Agent |
| subagent tool | `call_subagent` | 调用行业包内的供应、需求、风险等子 Agent |
| data tool | `read_rss`、`read_jina_url`、`shipping_tracker` | 获取证据和外部数据 |
| reasoning tool | `run_debate`、`score_analysis` | 执行辩论、评分、风险检查 |
| strategy tool | `generate_trade_plan`、`validate_trade_plan` | 生成或校验交易计划 |
| notification tool | `notify_user` | 通知用户或请求人工确认 |
| monitoring tool | `request_monitoring` | 请求后续盯盘或特征监控 |
| broker tool | `request_broker_action` | 请求交易通道动作；初版只做虚盘，不操作实盘 |

### 高风险工具

通知、盯盘和执行工具都必须是受控工具。

受控工具需要检查：

- 行业包配置。
- 用户授权。
- confidence score。
- risk flags。
- market / broker policy。
- 是否需要 human approval。
- 是否允许自动交易。

Agent 可以请求执行，但最终是否执行由工具背后的 Policy / Decision Gate 决定。

### 设计说明

工具必须先进入 ToolRegistry，再由 AgentRuntime 注入给 DeepAgents。

原因：

- 插件自定义工具需要统一命名、权限、参数 schema 和审计。
- DeepAgents 能接收工具，但工具治理不能交给单个插件自己处理。
- 工具权限需要结合 Agent、插件、用户设置和运行环境判断。

### Tool 定义

```text
ToolDefinition
  id
  name
  provider_plugin_id
  version
  description
  input_schema
  output_schema
  permissions
  risk_level
  timeout
  requires_human_approval
```

### 工具风险分级

| 风险等级 | 示例 | 策略 |
| --- | --- | --- |
| low | 读取公开 RSS、读取缓存事件 | 默认允许 |
| medium | 调用外部 API、抓取网页 | 需要限流和日志 |
| high | 写配置、触发通知、虚盘 broker | 需要审计，可要求确认 |
| critical | 真实交易执行 | 初版禁用 |

## 插件自定义工具

插件可以声明自定义工具，但不能直接绕过 ToolRegistry。

工具本身按插件式能力治理。Source、Industry、Strategy、Notification、broker 插件都可以暴露工具，但工具是否能被 Agent 使用，由 ToolRegistry、AgentRuntime 和权限策略共同决定。

### 推荐流程

```text
Plugin loads
  -> exposes tool definitions
  -> ToolRegistry validates schema and permissions
  -> AgentRuntime selects allowed tools
  -> DeepAgents receives concrete tools
```

### 约束

- 工具参数必须有 JSON Schema / Pydantic schema。
- 工具输出必须可序列化。
- 工具调用必须带 `event_id`、`agent_run_id` 和 `plugin_id`。
- 工具调用失败必须返回结构化错误。
- 高风险工具必须支持 human approval。

## Provider 管理

ProviderManager 负责多供应商模型接入。

### 设计说明

初版使用 LiteLLM SDK 作为 provider 抽象层。后续如果需要统一模型网关、集中限流、集中成本统计或跨服务共享 provider，再评估 LiteLLM Proxy。

原因：

- LiteLLM 支持多供应商统一 OpenAI 格式。
- 支持 fallback、routing、cost tracking、rate limit 等能力。
- 避免我们为 OpenAI、Anthropic、Gemini、Ollama、vLLM 等分别写 provider adapter。
- 后续部署为独立 LLM gateway 时迁移成本较低。

### ProviderPolicy

Agent 不直接指定具体 API key，只指定 provider policy。

```text
ProviderPolicy
  id
  default_model
  fallback_models
  max_tokens
  temperature
  timeout
  budget_limit
  allowed_providers
```

示例：

```yaml
provider_policy: balanced
```

### 初版策略

- `fast`：低成本、低延迟，用于路由和简单分类。
- `balanced`：默认策略，用于行业分析。
- `reasoning`：高质量模型，用于复杂 Debate / Scoring。
- `local`：本地模型，用于开发或隐私敏感场景。

## Workflow 编排

初版主流程：

```text
Event
  -> RouterAgent
  -> tool: dispatch_to_industry_agent
  -> IndustryAgentRuntime
  -> tool/subagent/debate loop
  -> Debate / Scoring
  -> Structured Output
  -> Decision
```

### RouterAgent

职责：

- 提取实体。
- 识别行业。
- 选择候选 Industry Plugin。
- 输出路由原因和置信度。

输出必须 schema 化：

```text
RoutingDecision
  event_id
  selected_industries
  rejected_industries
  entities
  reasoning_summary
  confidence
  requires_human_review
```

### IndustryAgentRuntime

职责：

- 根据行业包加载 AgentDefinition。
- 注入 event、industry_context、tools、risk_policy。
- 调用 DeepAgents 运行行业分析。
- 通过工具调用子 Agent、行业工具、数据工具、辩论工具和策略工具。
- 输出 `IndustryAnalysis` 和可选 `TradePlanDraft`。

### TradePlanDraft

行业主 Agent 可以产出交易计划草案，但它不是最终执行命令。

```text
TradePlanDraft
  event_id
  industry_plugin_id
  thesis
  target_instruments
  direction
  sizing_hint
  leverage_hint
  entry_conditions
  take_profit
  stop_loss
  monitoring_plan
  confidence_score
  risk_flags
  requires_human_approval
```

示例：

- 判断战争升级可能推动 Brent 原油上涨。
- 生成加仓 Brent 原油的计划草案。
- 给出仓位、杠杆、止盈止损和盯盘条件。
- 请求后续监控量价、K 线或成交量特征。

最终动作仍必须进入 Decision / Policy Gate。

### Debate / Scoring

职责：

- 聚合多个行业分析。
- 生成支持观点和反方观点。
- 标记不确定性。
- 输出标准置信度和风险标记。

推荐：

- Debate 流程由核心提供默认模板。
- 行业包可以提供自定义 scoring hints，但不能替代核心 Decision。

## 运行状态与持久化

Agent 运行需要记录摘要，不默认保存完整模型原始推理链。

### 建议记录

```text
agent_runs
agent_run_steps
tool_invocations
```

### 记录内容

- `agent_run_id`
- `event_id`
- `agent_definition_id`
- `agent_definition_version`
- `provider_policy`
- `model_used`
- `started_at`
- `ended_at`
- `status`
- `token_usage`
- `cost_estimate`
- `error_summary`
- `structured_output`

### 不默认记录

- 完整 CoT。
- 完整 provider 原始响应。
- 敏感工具参数。
- API key 或 secret 原文。

## 错误处理、超时和中断

### 推荐策略

- Provider 调用使用 timeout 和 retry。
- Tool 调用使用 timeout、retry 和 risk-level 控制。
- AgentRuntime 支持 cancel。
- 高风险工具使用 human approval。
- 失败输出结构化错误，进入 Decision 降级或人工确认。
- broker tool 失败或被拒绝时，不允许 Agent 自行重试绕过限制。

### 常见错误

- Provider timeout。
- Provider rate limit。
- Tool schema validation failed。
- Tool execution failed。
- Agent output schema invalid。
- Agent run canceled。

## 评估与回归测试

Agent 输出不稳定，必须设计基本评估机制。

### 初版建议

- 每个行业包提供少量 fixture events。
- 每个 AgentDefinition 提供 expected output shape。
- 用 pytest 做结构化输出和关键字段测试。
- 后续接入 LangSmith 或其他评估平台做 trace 和质量评估。

### 不做

- 初版不做复杂自动打分系统。
- 初版不把评估结果作为上线强门禁。

## 初版实现范围

必须实现：

- AgentRuntime。
- AgentDefinition frontmatter 解析。
- ToolRegistry。
- 插件自定义工具注册。
- ProviderManager。
- LiteLLM SDK 集成。
- RouterAgent schema 化输出。
- IndustryAnalysis schema 化输出。
- Agent run 摘要持久化。

暂缓实现：

- LiteLLM Proxy 独立网关。
- 复杂多 Agent 自主协商。
- 完整 CoT 存储。
- 大规模 Agent 评估平台。
- 生产级 provider 成本预算系统。

## 待确认问题

暂无。用户已确认本文档核心方案。

## 参考资料

- DeepAgents Python docs: https://docs.langchain.com/oss/python/deepagents/overview
- DeepAgents Python reference: https://reference.langchain.com/python/deepagents/deepagents
- LiteLLM docs: https://docs.litellm.ai/
