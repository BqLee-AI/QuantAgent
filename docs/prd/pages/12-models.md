# 12. Model Providers / LLM Policies

## 页面定位

Model Providers / LLM Policies 是 AgentRuntime 的模型供应商和 provider policy 治理入口。它管理模型供应商可用性、secret reference、fallback、预算、限流、成本和运行失败，不属于普通 Settings，也不属于插件配置。

现有设计中 ProviderManager 独立于 AgentDefinition。AgentDefinition 只声明 `provider_policy`，不直接绑定某个模型供应商、模型 API key 或 secret。

## 范围说明

本页只定义前端治理入口、信息结构和安全边界，不决定生产环境最终供应商、默认模型版本、预算阈值或 LiteLLM Proxy 部署形态。这些需要在后续 OpenSpec、配置 contract 和部署文档中继续收口。

模型供应商不是插件类型。插件可以提供 AgentDefinition、Skill、Tool 或行业能力，但模型选择、API key 引用、fallback 和预算必须由 AgentRuntime 的 ProviderManager / ProviderPolicy 统一治理，避免插件绕过模型策略和审计边界。

## 用户任务

- 查看当前可用的模型供应商和本地模型能力。
- 配置和审查 `fast`、`balanced`、`reasoning`、`local` 等 provider policy。
- 在具备权限时调整 provider 启停、secret reference 和 policy 字段。
- 执行脱敏连接检查，确认缺 key、限流、超时或模型不可用问题。
- 判断某次 AgentRun 使用了哪个 policy、哪个模型、消耗了多少 token 和成本。
- 发现 provider 缺 key、限流、超时、成本超预算或 fallback 失败。
- 进入相关 AgentRun 或 Runtime 错误排查。

## 主对象和真源

| 信息 | 真源 |
| --- | --- |
| Provider 状态 | ProviderManager |
| ProviderPolicy | 核心配置或后续持久化 policy 记录 |
| Provider 配置 | 环境变量、secret reference、运行时配置摘要 |
| Secret 引用 | secret reference，只显示引用不显示原文 |
| 用量和成本 | agent_runs 的 token_usage、cost_estimate、model_used |
| 失败和限流 | runtime_errors / provider 调用摘要 |
| Agent 关联 | AgentDefinition frontmatter 的 `provider_policy` 和 AgentRun 记录 |

## 页面结构

V1 页面结构应收敛为成熟软件常见的资源管理形态，而不是单表单页：

```text
系统设置导航
  -> 模型配置
       -> 中栏：Provider 列表
       -> 右栏：Provider 详情编辑
       -> 顶部或次级视图：任务模型预设
```

### Provider 列表区

Provider 列表区必须承担“找对象”和“看状态”的职责，至少包含：

- 搜索框
- 状态筛选：全部 / 已启用 / 默认 / 异常 / 缺少 Key
- 新增 Provider 按钮
- Provider 列表项

每个列表项至少展示：

- provider 名称
- provider 类型
- 默认标识
- 启用状态
- key 状态
- 最近连接或失败状态
- 模型数量
- 最近更新时间

### Provider 详情区

Provider 详情区承担“改对象”的职责，至少分为：

- 基本信息区
- 连接配置区
- 模型管理区
- 状态区
- Token 使用统计区

### 新增 Provider 入口

新增 Provider 不应只提供空白表单。V1 需要同时支持：

1. 从预置模板新增
2. 从空白自定义新增

预置模板至少包含：

- OpenAI
- Anthropic
- DeepSeek
- Qwen
- Moonshot
- OpenRouter
- 自定义 OpenAI-compatible

模板需要提供：

- 推荐显示名称
- 默认 base URL
- 推荐模型示例
- provider type

```text
页面头
  -> Provider 状态
  -> Policy 列表
  -> Usage & Cost
  -> Failures
  -> Agent policy 引用
```

## 路由与入口

路由：

```text
/models
```

主要入口：

- Governance 分组下的 Models。
- Runtime / Agent Run 详情中的 `provider_policy` 和 `model_used` 链接。
- Runtime error 中 provider 失败、限流或预算异常的链接。
- Plugin Detail 的 Industry / Strategy AgentDefinition 摘要中可链接到对应 policy。

不从 Dashboard 主入口进入，避免干扰操盘主链路。

## Provider 状态

必须展示：

- provider 名称，例如 OpenAI、Anthropic、Gemini、Ollama、vLLM、local。
- provider 类型：cloud / local / self_hosted。
- 状态：enabled / disabled / missing_secret / rate_limited / failed。
- secret reference 状态。
- 默认 endpoint 或运行环境摘要，必须脱敏。
- 最近一次成功调用时间。
- 最近一次失败摘要。
- 最近检测状态：未检测 / 成功 / 失败。

不展示：

- API key 原文。
- 完整请求体或响应体。
- 完整 provider 原始响应。

## ProviderPolicy 管理

V1 至少支持以下 policy：

- `fast`：低成本、低延迟，用于路由、分类和轻量判断。
- `balanced`：默认策略，用于行业分析。
- `reasoning`：高质量模型，用于复杂 Debate / Scoring。
- `local`：本地模型，用于开发或隐私敏感场景。

每个 policy 必须展示：

- `default_model`。
- `fallback_models`。
- `max_tokens`。
- `temperature`。
- `timeout`。
- `budget_limit`。
- `allowed_providers`。
- 当前状态。
- 最近失败和 fallback 结果。

## 操作与权限

允许动作：

- 只读查看 provider、policy、用量和失败摘要。
- 有对应 capability 的用户可以编辑 provider 启停、secret reference、endpoint 摘要和 policy 字段。
- 保存前必须校验 fallback 链路、allowed_providers、预算限制和受影响 AgentDefinition。
- 连接检查只能执行脱敏 smoke check，不发送真实事件、完整 prompt 或私有策略。
- provider 和 policy 变更必须写入 audit logs。

V1 额外要求：

- API key 应支持就地测试，不要求用户先保存后离开页面再验证。
- 用户切换 provider 时，若详情存在未保存变更，应给出明确提示。
- 空白 key 不得覆盖已保存 key。

不允许动作：

- 不允许单个插件维护独立 LLM API key。
- 不允许在本页编辑 AgentDefinition prompt、工具列表或行业规则。
- 不允许通过本页绕过 ProviderManager 直接指定模型请求参数。

## Usage & Cost

必须展示聚合摘要：

- 最近 24 小时 / 7 天 token usage。
- cost estimate。
- 按 provider 聚合。
- 按 provider policy 聚合。
- 按 model 聚合。
- 按 AgentRun 或 run_type 聚合。
- 超预算或接近预算提醒。

成本仅用于治理和排障，不作为交易建议评分。

## Failures

必须展示：

- provider timeout。
- rate limit。
- authentication failure。
- model unavailable。
- output invalid。
- fallback exhausted。
- budget exceeded。

每条失败应提供：

- 时间。
- provider。
- policy。
- model。
- 关联 AgentRun。
- trace_id / request_id。
- 脱敏错误摘要。

## Agent Policy 引用

页面应能展示哪些 AgentDefinition 使用了某个 provider policy。

示例：

```text
balanced
  -> quantagent.official.agent.oil_supply_analyst
  -> quantagent.official.agent.semiconductor_analyst
```

这只是引用关系，不允许在本页直接编辑 AgentDefinition prompt 或行业规则。

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| no_provider_configured | 展示空态和配置入口 |
| missing_secret | 标记 provider 不可用，只显示 secret reference 缺失 |
| rate_limited | 标记降级，展示 fallback 是否生效 |
| fallback_failed | 展示 fallback 链路和失败摘要 |
| budget_exceeded | 禁用或降级对应 policy，展示预算原因 |
| local_unavailable | local policy 显示不可用和运行环境说明 |
| 权限不足 | 禁用配置动作，只允许只读查看 |

## 安全边界

- API key 和 token 永不明文展示。
- secret 只以 secret reference 或 masked 状态出现。
- ProviderPolicy 修改属于高影响配置，必须有权限控制和审计。
- AgentDefinition 不能直接绑定 API key，只能引用 provider policy。
- 不保存或展示完整模型推理链、完整 prompt 或完整 provider 原始响应。
- 预算、fallback 和 provider 启停不能绕过 AgentRuntime。

## 验收口径

必须成立：

- 用户能知道系统当前可用哪些模型供应商。
- 用户能看懂 `fast`、`balanced`、`reasoning`、`local` 的用途和配置。
- 用户能从 AgentRun 回溯到 provider policy 和 model_used。
- 用户能定位 provider 失败、限流、缺 key、预算超限等问题。
- 用户能理解模型供应商不属于插件配置，也不属于普通 Settings。
- Settings 不承接模型供应商和模型策略配置。

失败信号：

- LLM API key 被放进普通 Settings。
- AgentDefinition 直接写具体 API key 或绕过 provider policy。
- 模型选择、fallback、预算和限流没有审计或权限边界。
- AgentRun 只显示“AI 运行失败”，无法定位 provider / policy / model。

## 非目标

- 不做 prompt 编辑器。
- 不做 AgentDefinition 编辑器。
- 不做生产级模型评估平台。
- 不做完整 observability / tracing 产品。
- 不做供应商账单系统。
