# Analysis Schema 设计

## 设计依据

本文档根据 `docs/design/02-core-architecture-and-runtime.md`、
`docs/design/04-database-and-persistence-design.md` 和
`docs/design/05-agent-workflow-design.md` 收敛 Analysis 相关数据库 schema。

Analysis 相关持久化采用“结构化摘要 + JSONB 演进载荷”的模型：

- 结构化字段保存高频查询、关联、状态、置信度、风险和动作结果。
- JSONB 保存仍在演进的分析摘要、证据摘要、评分细节和 Decision audit summary。
- 不默认保存完整模型原始推理链、完整 provider 原始响应、secret、私有策略或敏感工具参数。
- Agent、工具、行业包和 Decision 的关键运行过程必须可追踪、可回放、可审计。

初版 Analysis schema 包含七张表：

```text
agent_runs
agent_run_steps
tool_invocations
routing_decisions
industry_analyses
scored_analyses
decision_results
```

本文档不设计 Notification、Human Approval、统一 `audit_logs`、ToolRegistry 定义表或
Skill Registry 表；这些能力后续单独设计。

## 表关系

```text
events 1 ── 0..n agent_runs
agent_runs 1 ── 0..n agent_run_steps
agent_runs 1 ── 0..n tool_invocations
events 1 ── 0..n routing_decisions
events 1 ── 0..n industry_analyses
events 1 ── 0..n scored_analyses
events 1 ── 0..n decision_results
```

- `agent_runs` 记录 AgentRuntime 运行摘要。
- `agent_run_steps` 记录 Agent run 的步骤摘要。
- `tool_invocations` 记录受控工具调用摘要。
- `routing_decisions` 记录 Router Agent 输出。
- `industry_analyses` 记录行业包统一输出。
- `scored_analyses` 记录 Debate / Scoring 聚合结果。
- `decision_results` 记录 Decision / Policy Gate 输出。

## 枚举与状态

### `agent_run_status`

| 值 | 说明 |
| --- | --- |
| `pending` | 运行已创建但尚未开始 |
| `running` | 运行中 |
| `succeeded` | 成功完成并产出有效结构化输出 |
| `failed` | 运行失败 |
| `canceled` | 被用户、系统或调度器取消 |
| `timed_out` | 因超时终止 |
| `output_invalid` | Agent 输出不符合目标 schema |

### `analysis_status`

| 值 | 说明 |
| --- | --- |
| `pending` | 记录已创建但结果未完成 |
| `succeeded` | 分析、评分或决策成功完成 |
| `failed` | 处理失败 |
| `canceled` | 被取消 |
| `output_invalid` | 输出结构不符合 schema |
| `superseded` | 被后续重新分析结果替代 |

### `tool_invocation_status`

| 值 | 说明 |
| --- | --- |
| `pending` | 调用已登记但尚未执行 |
| `running` | 工具执行中 |
| `succeeded` | 工具执行成功 |
| `failed` | 工具执行失败 |
| `canceled` | 工具调用被取消 |
| `timed_out` | 工具调用超时 |
| `blocked` | 权限、风险策略或人工确认阻止调用 |

### `decision_action`

| 值 | 说明 |
| --- | --- |
| `notify_only` | 只通知，不请求人工确认或执行 |
| `request_human_approval` | 请求人工确认 |
| `dry_run_broker` | 允许进入虚盘 broker；协议值保留 `dry_run_broker` |
| `reject` | 拒绝后续动作 |

初版不支持 `execute_trade`。

## `agent_runs`

### 用途

`agent_runs` 记录 AgentRuntime 的一次运行摘要，用于运行追踪、成本统计、错误排查和后续审计串联。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | Agent run ID |
| `event_id` | `uuid` | not null, foreign key | 关联事件 ID |
| `run_type` | `text` | not null | 运行类型，例如 `router`、`industry_analysis`、`scoring`、`debate` |
| `agent_definition_id` | `text` | nullable | AgentDefinition ID；非 Agent 运行或默认 scoring 流程可以为空 |
| `agent_definition_version` | `text` | nullable | AgentDefinition 版本 |
| `provider_policy` | `text` | nullable | 使用的 provider policy，例如 `fast`、`balanced`、`reasoning`、`local` |
| `model_used` | `text` | nullable | 实际使用的模型名称 |
| `status` | `text` | not null | Agent run 当前状态，按 `agent_run_status` 值约束 |
| `input_summary` | `jsonb` | not null, default `{}` | 输入摘要，例如 event、slots、authorized tools 的脱敏摘要 |
| `structured_output` | `jsonb` | nullable | 结构化输出快照；只保存 schema 化结果，不保存完整 CoT |
| `token_usage` | `jsonb` | not null, default `{}` | token 使用统计，例如 prompt、completion、total |
| `cost_estimate` | `numeric(18, 8)` | nullable | 运行成本估算，币种由 `cost_currency` 表示 |
| `cost_currency` | `text` | nullable | 成本币种，例如 `USD` |
| `trace_id` | `text` | not null | 跨事件、Agent、工具和 Decision 的追踪 ID |
| `correlation_id` | `text` | nullable | 与 Event Envelope 或上游任务关联的 correlation ID |
| `provider_trace_ref` | `text` | nullable | 外部 tracing 系统引用，例如 LangSmith 或 OpenTelemetry trace ID |
| `started_at` | `timestamptz` | nullable | 运行开始时间 |
| `ended_at` | `timestamptz` | nullable | 运行结束时间 |
| `duration_ms` | `integer` | nullable | 运行耗时毫秒数 |
| `error_code` | `text` | nullable | 失败时的结构化错误码 |
| `error_message` | `text` | nullable | 失败时的脱敏错误摘要 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、完整推理链或敏感工具参数 |
| `created_at` | `timestamptz` | not null, default `now()` | 记录创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 记录最近更新时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `index(event_id, created_at desc)`，支持查看某个事件的 Agent 运行历史。
- `index(run_type, status)`，支持按运行类型和状态排查。
- `index(status, created_at desc)`，支持运行工作台按状态读取。
- `index(trace_id)`，支持跨表追踪。
- `index(correlation_id)`，支持按上游任务或 envelope 追踪。

### 写入规则

- AgentRuntime 创建运行时先写 `pending` 或 `running` 记录。
- 运行结束时更新 `status`、`ended_at`、`duration_ms`、`structured_output` 或错误字段。
- 不保存完整 provider 原始响应和完整模型推理链；如需调试，保存外部 trace 引用或脱敏摘要。

## `agent_run_steps`

### 用途

`agent_run_steps` 以追加方式记录 Agent run 的步骤摘要，帮助重建运行轨迹，但不保存完整模型思维过程。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 步骤记录 ID |
| `agent_run_id` | `uuid` | not null, foreign key | 所属 Agent run ID |
| `event_id` | `uuid` | not null, foreign key | 冗余事件 ID，便于按事件查询步骤 |
| `step_index` | `integer` | not null | 步骤序号，在同一 Agent run 内递增 |
| `step_type` | `text` | not null | 步骤类型，例如 `model_call`、`tool_call`、`subagent_call`、`schema_validation`、`scoring` |
| `name` | `text` | nullable | 步骤名称，例如工具名、子 Agent 名或校验阶段名 |
| `status` | `text` | not null | 步骤状态，按 `agent_run_status` 值约束 |
| `input_summary` | `jsonb` | not null, default `{}` | 步骤输入脱敏摘要 |
| `output_summary` | `jsonb` | nullable | 步骤输出脱敏摘要 |
| `token_usage` | `jsonb` | not null, default `{}` | 该步骤 token 使用统计 |
| `cost_estimate` | `numeric(18, 8)` | nullable | 该步骤成本估算 |
| `started_at` | `timestamptz` | nullable | 步骤开始时间 |
| `ended_at` | `timestamptz` | nullable | 步骤结束时间 |
| `duration_ms` | `integer` | nullable | 步骤耗时毫秒数 |
| `error_code` | `text` | nullable | 步骤失败时的结构化错误码 |
| `error_message` | `text` | nullable | 步骤失败时的脱敏错误摘要 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存完整 CoT、secret 或敏感参数 |
| `created_at` | `timestamptz` | not null, default `now()` | 记录创建时间 |

### 约束与索引

- `agent_run_id` 外键引用 `agent_runs.id`，建议 `on delete restrict`。
- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `agent_run_steps.event_id` 必须与关联 `agent_runs.event_id` 一致；落地时可通过复合外键约束或 service 层写入校验保证。
- `unique(agent_run_id, step_index)`，保证同一运行内步骤序号稳定。
- `index(agent_run_id, step_index asc)`，支持按顺序读取运行轨迹。
- `index(event_id, created_at desc)`，支持按事件读取步骤。
- `index(step_type, status)`，支持排查特定步骤类型。

### 写入规则

- 该表保存步骤摘要，不保存完整 provider 原始响应。
- 写入时必须校验冗余 `event_id` 与所属 `agent_run_id` 指向的事件一致，避免事件回放和统计漂移。
- 工具调用的详细输入输出摘要应写入 `tool_invocations`，步骤中只保留关联摘要。
- 步骤记录原则上追加；如运行中需要更新状态，只更新当前步骤的状态和结束字段，不改写已完成步骤语义。

## `tool_invocations`

### 用途

`tool_invocations` 记录 Agent、插件或核心运行时通过 ToolRegistry 发起的受控工具调用摘要。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 工具调用 ID |
| `event_id` | `uuid` | not null, foreign key | 关联事件 ID |
| `agent_run_id` | `uuid` | nullable, foreign key | 触发该工具调用的 Agent run ID；非 Agent 触发时可为空 |
| `agent_run_step_id` | `uuid` | nullable, foreign key | 关联 Agent run step ID |
| `tool_id` | `text` | not null | ToolRegistry 中的工具 ID |
| `tool_name` | `text` | nullable | 工具展示名或调用名 |
| `provider_plugin_id` | `text` | nullable | 提供该工具的插件 ID；核心内置工具可为空 |
| `provider_plugin_version` | `text` | nullable | 提供该工具的插件版本 |
| `risk_level` | `text` | not null | 工具风险等级，建议值为 `low`、`medium`、`high`、`critical` |
| `requires_human_approval` | `boolean` | not null, default `false` | 调用该工具是否需要人工确认 |
| `status` | `text` | not null | 工具调用状态，按 `tool_invocation_status` 值约束 |
| `input_summary` | `jsonb` | not null, default `{}` | 工具输入脱敏摘要，不保存 secret 或敏感参数原文 |
| `output_summary` | `jsonb` | nullable | 工具输出脱敏摘要，必须可序列化 |
| `input_schema_hash` | `text` | nullable | 调用时使用的输入 schema hash |
| `output_schema_hash` | `text` | nullable | 调用时使用的输出 schema hash |
| `timeout_ms` | `integer` | nullable | 本次工具调用超时配置 |
| `retry_count` | `integer` | not null, default `0` | 已执行的重试次数 |
| `trace_id` | `text` | not null | 跨表追踪 ID |
| `started_at` | `timestamptz` | nullable | 工具调用开始时间 |
| `ended_at` | `timestamptz` | nullable | 工具调用结束时间 |
| `duration_ms` | `integer` | nullable | 工具调用耗时毫秒数 |
| `error_code` | `text` | nullable | 工具调用失败或被阻塞时的错误码 |
| `error_message` | `text` | nullable | 工具调用失败或被阻塞时的脱敏错误摘要 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、私有策略或敏感工具参数 |
| `created_at` | `timestamptz` | not null, default `now()` | 记录创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 记录最近更新时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `agent_run_id` 外键引用 `agent_runs.id`，建议 `on delete set null`。
- `agent_run_step_id` 外键引用 `agent_run_steps.id`，建议 `on delete set null`。
- 当 `agent_run_id` 非空时，`tool_invocations.event_id` 必须与关联 `agent_runs.event_id` 一致。
- 当 `agent_run_step_id` 非空时，`tool_invocations.event_id` 必须与关联 `agent_run_steps.event_id` 一致。
- 当 `agent_run_id` 和 `agent_run_step_id` 同时非空时，关联的 `agent_run_steps.agent_run_id` 必须等于 `tool_invocations.agent_run_id`。
- `index(event_id, created_at desc)`，支持事件轨迹展示。
- `index(agent_run_id, created_at asc)`，支持 Agent run 工具调用回放。
- `index(tool_id, status)`，支持按工具排查失败。
- `index(provider_plugin_id, created_at desc)`，支持按插件排查工具调用。
- `index(risk_level, status)`，支持筛选高风险工具调用。
- `index(trace_id)`，支持跨表追踪。

### 写入规则

- 所有 Agent 外部行动都应表达为工具调用，并写入本表。
- 写入时必须由 service 层校验 `event_id`、`agent_run_id`、`agent_run_step_id` 的一致性；如果后续需要数据库强约束，可通过复合外键或触发器补齐。
- 高风险工具被策略阻止时，仍应写入 `status = blocked` 和阻塞原因。
- 工具调用触发的审批由 `approval_records.tool_invocation_id` 反查，本表不保存 `approval_record_id`，避免双向 nullable 关系漂移。
- 工具输入输出必须脱敏；API key、secret、账户信息和敏感工具参数不得明文入库。

## `routing_decisions`

### 用途

`routing_decisions` 保存 Router Agent 对事件的路由结果，用于选择候选行业包和解释路由原因。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 路由结果 ID |
| `event_id` | `uuid` | not null, foreign key | 被路由的事件 ID |
| `agent_run_id` | `uuid` | nullable, foreign key | 生成该路由结果的 Agent run ID |
| `router_agent_id` | `text` | nullable | Router AgentDefinition ID |
| `router_agent_version` | `text` | nullable | Router AgentDefinition 版本 |
| `selected_industries` | `jsonb` | not null, default `[]` | 选中的行业插件列表，包含插件 ID、版本、原因摘要等 |
| `rejected_industries` | `jsonb` | not null, default `[]` | 被拒绝的候选行业插件列表和原因摘要 |
| `entities` | `jsonb` | not null, default `[]` | Router 提取的实体数组 |
| `reasoning_summary` | `text` | nullable | 路由原因摘要，不保存完整推理链 |
| `confidence_score` | `numeric(5, 4)` | nullable | 路由置信度，建议范围 0 到 1 |
| `requires_human_review` | `boolean` | not null, default `false` | 低置信度或高风险路由是否需要人工复核 |
| `status` | `text` | not null | 路由结果状态，按 `analysis_status` 值约束 |
| `raw_output` | `jsonb` | nullable | Router schema 化输出快照，不保存完整 provider 原始响应 |
| `trace_id` | `text` | not null | 跨表追踪 ID |
| `created_at` | `timestamptz` | not null, default `now()` | 创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 更新时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `agent_run_id` 外键引用 `agent_runs.id`，建议 `on delete set null`。
- `index(event_id, created_at desc)`，支持查看事件路由历史。
- `index(status, created_at desc)`，支持排查失败或待复核路由。
- `index(requires_human_review, created_at desc)`，支持人工复核队列。
- `index(trace_id)`，支持跨表追踪。

### 写入规则

- Router Agent 不直接给交易建议，只输出行业路由、实体和原因摘要。
- 一个事件可以有多次路由结果；后续重路由不删除历史路由记录。
- 低置信度结果应设置 `requires_human_review = true` 或进入仅通知/复核路径。

## `industry_analyses`

### 用途

`industry_analyses` 保存行业包统一结构化输出，供 Scoring / Debate 和 Decision 使用。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 行业分析 ID |
| `event_id` | `uuid` | not null, foreign key | 被分析的事件 ID |
| `routing_decision_id` | `uuid` | nullable, foreign key | 触发该行业分析的路由结果 ID |
| `agent_run_id` | `uuid` | nullable, foreign key | 生成该行业分析的 Agent run ID |
| `industry_plugin_id` | `text` | not null | 行业包插件 ID |
| `industry_plugin_version` | `text` | not null | 行业包插件版本 |
| `status` | `text` | not null | 行业分析状态，按 `analysis_status` 值约束 |
| `impact_summary` | `text` | nullable | 行业影响摘要 |
| `first_order_impacts` | `jsonb` | not null, default `[]` | 一阶影响列表 |
| `second_order_impacts` | `jsonb` | not null, default `[]` | 二阶影响列表 |
| `affected_markets` | `jsonb` | not null, default `[]` | 受影响市场列表 |
| `affected_instruments` | `jsonb` | not null, default `[]` | 受影响标的列表 |
| `evidence` | `jsonb` | not null, default `[]` | 证据摘要列表，不保存大规模网页快照 |
| `counter_arguments` | `jsonb` | not null, default `[]` | 反方观点摘要 |
| `confidence_score` | `numeric(5, 4)` | nullable | 行业分析置信度，建议范围 0 到 1 |
| `recommended_actions` | `jsonb` | not null, default `[]` | 行业包建议动作，只是建议，不是最终 Decision |
| `risk_flags` | `jsonb` | not null, default `[]` | 风险标记数组 |
| `requires_verification` | `boolean` | not null, default `false` | 是否需要额外验证 |
| `trade_plan_draft` | `jsonb` | nullable | 可选交易计划草案；不是最终执行命令 |
| `raw_output` | `jsonb` | nullable | 行业分析 schema 化输出快照 |
| `trace_id` | `text` | not null | 跨表追踪 ID |
| `created_at` | `timestamptz` | not null, default `now()` | 创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 更新时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `routing_decision_id` 外键引用 `routing_decisions.id`，建议 `on delete set null`。
- `agent_run_id` 外键引用 `agent_runs.id`，建议 `on delete set null`。
- `index(event_id, created_at desc)`，支持查看事件分析历史。
- `index(industry_plugin_id, industry_plugin_version)`，支持按行业包版本回查分析。
- `index(status, created_at desc)`，支持排查失败或待处理分析。
- `index(confidence_score)`，支持按置信度筛选。
- `index(trace_id)`，支持跨表追踪。

### 写入规则

- 行业包输出必须符合统一 `IndustryAnalysis` 结构。
- 行业包可以提供 `trade_plan_draft`，但不能绕过 Decision / Policy Gate 直接执行。
- 多个行业包可以对同一事件各自产生分析，历史分析不被新分析覆盖。

## `scored_analyses`

### 用途

`scored_analyses` 保存 Scoring / Debate 对多个行业分析的聚合结果，作为 Decision 的主要输入。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 评分分析 ID |
| `event_id` | `uuid` | not null, foreign key | 被评分的事件 ID |
| `agent_run_id` | `uuid` | nullable, foreign key | 生成评分结果的 Agent run ID |
| `status` | `text` | not null | 评分结果状态，按 `analysis_status` 值约束 |
| `analysis_ids` | `jsonb` | not null, default `[]` | 被聚合的 `industry_analyses.id` 列表 |
| `support_arguments` | `jsonb` | not null, default `[]` | 支持观点摘要 |
| `counter_arguments` | `jsonb` | not null, default `[]` | 反方观点摘要 |
| `evidence_quality` | `jsonb` | not null, default `{}` | 证据质量摘要，例如数量、来源、可信度 |
| `confidence_score` | `numeric(5, 4)` | nullable | 聚合后的标准置信度，建议范围 0 到 1 |
| `risk_flags` | `jsonb` | not null, default `[]` | 聚合后的风险标记 |
| `recommended_actions` | `jsonb` | not null, default `[]` | 聚合后的建议动作 |
| `decision_hints` | `jsonb` | not null, default `{}` | 给 Decision 的结构化提示 |
| `scoring_details` | `jsonb` | nullable | 评分细节摘要，不保存完整推理链 |
| `trace_id` | `text` | not null | 跨表追踪 ID |
| `created_at` | `timestamptz` | not null, default `now()` | 创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 更新时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `agent_run_id` 外键引用 `agent_runs.id`，建议 `on delete set null`。
- `index(event_id, created_at desc)`，支持查看事件评分历史。
- `index(status, created_at desc)`，支持排查评分失败或待处理记录。
- `index(confidence_score)`，支持按置信度筛选。
- `index(trace_id)`，支持跨表追踪。

### 写入规则

- Decision 应基于聚合后的 `scored_analyses`，而不是单个行业包自说自话。
- `analysis_ids` 初版使用 JSONB 保存，数据库不保证其中 ID 的引用完整性；service 写入时必须校验所有 ID 指向同一 `event_id` 下存在的 `industry_analyses`。后续如果需要 DB 强约束和复杂查询，可拆成 `scored_analysis_items` 关联表。
- Scoring / Debate 不保存完整模型推理链，只保存支持观点、反方观点、证据质量和评分摘要。

## `decision_results`

### 用途

`decision_results` 保存 Decision / Policy Gate 的最终输出，用于通知、人工确认、虚盘或拒绝后续动作。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | Decision 结果 ID |
| `event_id` | `uuid` | not null, foreign key | 被决策的事件 ID |
| `scored_analysis_id` | `uuid` | nullable, foreign key | Decision 使用的评分分析 ID |
| `agent_run_id` | `uuid` | nullable, foreign key | 如果 Decision 由 AgentRuntime 辅助生成，则记录对应 run ID |
| `action` | `text` | not null | Decision 动作，按 `decision_action` 值约束，初版不包含实盘交易执行 |
| `status` | `text` | not null | Decision 结果状态，按 `analysis_status` 值约束 |
| `reason` | `text` | nullable | 决策原因摘要 |
| `confidence_score` | `numeric(5, 4)` | nullable | Decision 使用或输出的置信度 |
| `required_approval` | `boolean` | not null, default `false` | 是否需要人工确认 |
| `allowed_brokers` | `jsonb` | not null, default `[]` | 被允许的 broker 列表；初版只允许虚盘或 mock 语义，虚盘对应协议值 `dry_run` |
| `blocked_brokers` | `jsonb` | not null, default `[]` | 被阻止的 broker 列表及原因摘要 |
| `risk_flags` | `jsonb` | not null, default `[]` | Decision 采纳的风险标记 |
| `recommended_actions` | `jsonb` | not null, default `[]` | Decision 后续建议动作，例如通知、复核、虚盘；虚盘对应协议值 `dry_run` |
| `policy_snapshot` | `jsonb` | not null, default `{}` | 决策时使用的策略摘要，不保存私有策略全文或 secret |
| `audit_summary` | `jsonb` | not null, default `{}` | 审计摘要，用于后续写入统一 audit log |
| `trace_id` | `text` | not null | 跨表追踪 ID |
| `created_at` | `timestamptz` | not null, default `now()` | 创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 更新时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `scored_analysis_id` 外键引用 `scored_analyses.id`，建议 `on delete set null`。
- `agent_run_id` 外键引用 `agent_runs.id`，建议 `on delete set null`。
- `index(event_id, created_at desc)`，支持查看事件决策历史。
- `index(action, status)`，支持按动作和状态查询。
- `index(required_approval, created_at desc)`，支持人工确认队列前置查询。
- `index(trace_id)`，支持跨表追踪。

### 写入规则

- Decision 独立于行业包，行业包不能直接决定是否执行。
- 初版动作只允许 `notify_only`、`request_human_approval`、`dry_run_broker`、`reject`。
- 实盘交易执行不进入初版 schema；即使 broker 插件存在，也必须受配置、权限、风险和人工确认共同放行。
- Decision 生成后应在同一业务事务内更新事件状态，并追加事件状态流转记录。

## 验证建议

落地 ORM model 和 Alembic migration 时，至少验证：

- 空库 upgrade 后包含七张 Analysis 表、枚举、外键和关键索引。
- Agent run 可以记录状态、结构化输出、token 使用和脱敏错误摘要。
- Tool invocation 对高风险被阻止的工具也会写入 `blocked` 记录。
- RoutingDecision、IndustryAnalysis、ScoredAnalysis 和 DecisionResult 均可按 `event_id` 回放。
- JSONB 字段不保存完整模型推理链、完整 provider 原始响应、secret 或敏感工具参数。
- Decision action 不包含 `execute_trade`。
- Decision 结果与事件状态流转能在同一事务边界内写入。

## 后续扩展

- 如果 `scored_analyses.analysis_ids` 需要强约束，可拆出 `scored_analysis_items` 关联表。
- 如果 ToolRegistry 需要持久化工具定义，可单独设计 `tool_definitions` 和工具权限表。
- 如果 Provider 成本统计需要生产级精度，可增加 provider usage 明细表。
- 统一 `audit_logs` 落地后，Agent run、工具调用、高风险动作和 Decision 生成都应写 audit。
