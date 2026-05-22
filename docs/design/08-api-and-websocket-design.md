# 08. API 与实时通道设计

## 文档状态

**状态**：正式草案 v0.2  
**范围**：FastAPI REST API、实时状态通道、前后端契约、插件配置 API、HITL 授权 API、运行时可观测接口  
**当前约定**：后端使用 FastAPI，前端使用 React + Vite，前后端契约通过 OpenAPI / JSON Schema 生成 TypeScript 类型、client 和必要的 Zod 校验  
**不包含**：完整 endpoint 字段级定义、生产级多租户权限、GraphQL、交易所真实下单 API 细节

## 设计原则

- REST API 是业务状态真源的访问入口。
- 实时通道只负责状态变化通知，不保存业务状态，不替代 REST 查询。
- API 采用资源 REST 为主，`actions` endpoint 为辅。
- API DTO 必须独立于 ORM model，禁止直接返回 ORM model。
- 接口响应统一使用 `code/data/msg/error` envelope。
- Web 前端、插件后台、Agent 运行调试、HITL 授权、通知和 executor 能力都必须有可查询、可审计接口；初版 executor 只做虚盘，不操作实盘。
- 虚盘在 API、WebSocket topic 和 action type 中仍使用 `dry_run` 命名，不新增并行字段名。
- 插件配置、secret、交易策略、私有关键词、prompt 和敏感上下文不得通过 API 明文泄露。
- 任何高风险动作最终都必须经过 Policy Gate，不能只靠前端按钮、文本回复或 AI 判断绕过风控。

## API 资源模型

API 按资源建模，副作用操作统一放在资源下的 `actions` 路径。

示例：

```text
GET  /plugins
GET  /plugins/{plugin_id}
POST /plugins/{plugin_id}/actions/enable
POST /plugins/{plugin_id}/actions/disable

GET  /approvals/{approval_id}
POST /approvals/{approval_id}/actions/approve
POST /approvals/{approval_id}/actions/reject
```

这样做的原因：

- 事件、插件、Agent run、审批、通知、调度记录都天然有持久化状态。
- 启用、停用、安装、手动触发、批准、拒绝、重分析等操作是命令，不应该混在普通更新接口里。
- 前端状态管理、OpenAPI client 和审计记录都能围绕稳定资源展开。

## API DTO 分层

后端使用 Pydantic 定义 API request / response DTO。ORM model 只负责数据库映射，不直接作为 API DTO、Event DTO 或 Plugin DTO。

分层建议：

```text
ORM Model
  -> Repository
  -> Domain Object / Service Result
  -> API DTO
  -> ApiResponse<T>
```

核心跨语言对象需要额外输出 JSON Schema：

- `Event`
- `PluginManifest`
- `ToolDefinition`
- `SkillMetadata`
- `IndustryAnalysis`
- `Decision`
- `ActionRequest`
- `ApprovalRequest`
- `ApprovalEvaluation`
- `RealtimeEnvelope`

原因：

- Python 后端使用 Pydantic 与 FastAPI 集成最自然。
- TypeScript 前端需要稳定类型和运行时校验。
- JSON Schema / Zod 只覆盖跨语言契约，不强制所有内部对象一次性 schema 化。

## 前后端契约目录

契约文件放在 `packages/contracts`。

```text
packages/contracts/
  openapi/
    quantagent.openapi.json
  schemas/
    event.schema.json
    plugin.schema.json
    tool.schema.json
    skill.schema.json
    approval.schema.json
    realtime.schema.json
  generated/
    typescript/
      client/
      types/
      zod/
```

规则：

- REST client 从 OpenAPI 生成。
- 稳定领域对象从 JSON Schema 生成 TypeScript 类型和 Zod schema。
- 前端表单、WebSocket 消息、插件配置校验可以复用 Zod。
- 生成代码不得手动修改，应通过生成脚本更新。

## API 响应结构

所有 HTTP API 返回统一 envelope。

```text
ApiResponse<T>
  code
  data
  msg
  error
```

成功示例：

```json
{
  "code": 0,
  "data": {
    "id": "plugin_123",
    "status": "enabled"
  },
  "msg": "ok",
  "error": null
}
```

失败示例：

```json
{
  "code": 400100,
  "data": null,
  "msg": "Plugin config validation failed.",
  "error": {
    "code": "PLUGIN_CONFIG_INVALID",
    "request_id": "req_123",
    "trace_id": "trace_456",
    "details": {},
    "retryable": false
  }
}
```

字段说明：

| 字段 | 含义 |
| --- | --- |
| `code` | 业务状态码，成功为 `0` |
| `data` | 成功响应数据，失败时通常为 `null` |
| `msg` | 面向用户或前端的简短消息 |
| `error` | 结构化错误详情，成功时为 `null` |

规则：

- HTTP status 仍然保留，例如参数错误为 400，未授权为 401，系统错误为 500。
- 前端业务判断优先使用 `code`。
- 表单校验错误放入 `error.details.fields`。
- 插件、工具、AgentRuntime、Scheduler 抛出的错误需要转换为统一 `ApiError`。
- 错误响应不得包含密钥、完整 prompt、私有策略明文或敏感配置。

## 实时通道选型

初版采用 Native WebSocket + topic envelope。Socket.IO 作为后续适配层候选，不作为初版默认协议。

原因：

- FastAPI 原生支持 WebSocket，和当前 Python 后端技术栈贴合。
- 实时通道当前只负责后台状态通知，不负责业务状态真源。
- REST API、数据库状态和审计记录才是恢复状态的基础，连接层不应该承载核心可靠性。
- Socket.IO 的自动重连、long-polling fallback、ack、room 很有价值，但它不是裸 WebSocket，会引入专用协议和 Python server 适配层复杂度。
- 后续如果出现复杂网络、移动端长连接、多用户房间订阅等需求，可以在保持 topic / envelope 语义不变的前提下增加 Socket.IO adapter。

实时通道用途：

- Agent run 进度更新。
- Tool invocation 状态变化。
- HITL 授权请求到达提醒。
- 插件安装、启停、reload 状态变化。
- Scheduler run 状态变化。
- Notification / executor 状态变化；初版 executor 状态只覆盖虚盘，不操作实盘。
- Runtime error 提醒。

实时通道不负责：

- 保存业务状态。
- 替代 REST 查询。
- 承载最终授权判断。
- 向 QQ、微信、Telegram 等文本渠道直接推送消息。

## 实时消息订阅

实时通道采用 topic subscribe 模型，复用核心运行时的 EventEnvelope / Topic 设计。

示例 topic：

```text
source.event.captured
event.routed
industry.analysis.completed
decision.created
approval.requested
notification.completed
executor.dry_run_completed
runtime.failed
```

客户端订阅：

```json
{
  "type": "subscribe",
  "topics": [
    "event.routed",
    "industry.analysis.completed",
    "approval.requested",
    "runtime.failed"
  ],
  "last_seq": 1024
}
```

服务端消息：

```json
{
  "id": "msg_123",
  "topic": "approval.requested",
  "type": "approval.created",
  "payload": {},
  "correlation_id": "corr_123",
  "causation_id": "msg_122",
  "producer": "decision",
  "created_at": "2026-05-11T10:00:00Z",
  "seq": 1025
}
```

规则：

- 消息必须有 `topic`、`type`、`payload`、`created_at`。
- `correlation_id` 用于串联同一次事件处理链路。
- `causation_id` 用于表达消息因果关系。
- `seq` 初版可只保证单进程递增，后续升级为持久化 cursor。
- 客户端收到关键 topic 后，应按需触发 REST refresh。
- 实时消息不得返回敏感配置明文。
- 如果未来切换到 Socket.IO，topic 可以映射为 room，EventEnvelope 保持不变。

## 断线重连与状态恢复

初版采用“实时通知 + REST 快照恢复”。

流程：

```text
WebSocket disconnected
  -> client reconnects
  -> client refreshes current page REST snapshot
  -> client resumes topic subscription
```

规则：

- WebSocket 消息只是增量提醒，不作为页面状态唯一来源。
- 页面初始化必须通过 REST 获取完整快照。
- 断线重连后优先刷新当前页面相关资源。
- envelope 中保留 `seq` / `cursor` 字段，后续可升级为 outbox replay。
- 早期如果前端不需要实时体验，可以先用 REST 轮询，保留 WebSocket 协议边界。

## 插件配置 API

插件配置后台采用 schema-driven form，不做插件自定义前端组件。

接口能力：

```text
GET  /plugins/{plugin_id}/config-schema
GET  /plugins/{plugin_id}/config
POST /plugins/{plugin_id}/config:validate
PUT  /plugins/{plugin_id}/config
```

规则：

- 插件必须通过 `config_schema` 声明配置结构。
- 前端根据 schema 动态渲染配置表单。
- 敏感字段只返回 masked value 或 secret reference。
- 插件配置更新必须写 audit。
- 配置更新后是否需要 reload 由 Registry 和插件 manifest 决定。
- 特别复杂的配置体验后续可以增加 UI schema，但初版不允许插件注入自定义前端代码。

## HITL 授权模型

HITL 不能只按 Web UI 的 approve / reject 按钮理解。它本质是高风险动作的人类授权或确认，但授权输入可能来自 Web、一次性链接、QQ、微信、Telegram、Discord、邮件、本地 CLI 或自然语言文本。

系统采用以下链路：

```text
ActionRequest
  -> ApprovalPolicyResolver
  -> ApprovalRequest
  -> ApprovalInput
  -> ApprovalEvaluation
  -> ApprovalDecision
  -> Policy Gate
  -> Executor / Notification / Reanalysis
```

### ActionRequest

ActionRequest 是 Agent、Decision 或工具发出的动作请求。

```text
ActionRequest
  id
  action_type
  action_side
  target_type
  target_id
  instrument
  market
  amount
  leverage
  confidence_score
  risk_flags
  urgency
  proposed_payload
  strategy_policy
  user_policy
  ai_policy_hint
```

关键字段：

| 字段 | 含义 |
| --- | --- |
| `action_type` | 动作类型，例如 notify、monitor、dry_run、execute_order、reduce_position |
| `action_side` | 风险方向，例如 increase_risk、reduce_risk、neutral |
| `urgency` | 时效等级 |
| `strategy_policy` | 策略插件提供的约束 |
| `user_policy` | 用户配置的授权偏好 |
| `ai_policy_hint` | AI 根据规范建议的审批模式 |

### ApprovalPolicyResolver

ApprovalPolicyResolver 根据动作类型、风险方向、时效、用户配置、策略规则和 AI policy hint 决定授权策略。

输出：

```text
ResolvedApprovalPolicy
  mode
  required_confirmation_level
  expires_at
  expiration_action
  allowed_channels
  reason_summary
```

`mode` 支持：

| 模式 | 含义 |
| --- | --- |
| `no_approval_notify_only` | 不需要审批，只通知 |
| `execute_then_notify` | 立即执行，执行后通知 |
| `approval_required` | 必须等待人类输入 |
| `approval_with_timeout` | 限时等待，超时执行 expiration_action |
| `manual_only` | 只能强人工确认 |
| `blocked` | 直接阻断 |

规则：

- AI 可以建议审批模式，但不能直接绕过 Policy Gate。
- 系统底线规则优先级最高。
- 用户配置优先级高于策略插件默认建议。
- 增加风险动作默认需要更强确认。
- 降低风险动作可以按用户预授权更快执行。
- 所有策略解析结果必须可审计。

### ApprovalRequest

ApprovalRequest 表示系统需要人类介入或等待时效结果。

```text
ApprovalRequest
  id
  target_type
  target_id
  action_type
  action_side
  risk_level
  urgency
  summary
  proposed_payload
  required_confirmation_level
  expires_at
  expiration_action
  policy_source
  status
```

`required_confirmation_level` 分级：

| 等级 | 含义 | 示例 |
| --- | --- | --- |
| `informational` | 只通知，不需要确认 | 普通分析完成 |
| `soft_confirm` | 文本同意可以接受 | 发送通知、继续分析、低风险虚盘 |
| `strong_confirm` | 需要明确结构化确认 | 开启盯盘、调整策略参数 |
| `link_confirm` | 需要一次性链接确认 | 高风险交易请求、启用 executor |
| `manual_only` | 只能 Web 后台或本地控制台确认 | 真实下单、大额杠杆、敏感插件启用 |

`urgency` 分级：

| 等级 | 含义 | 示例 |
| --- | --- | --- |
| `low` | 不敏感，小时级有效 | 插件配置变更、普通复盘 |
| `normal` | 常规时效，几十分钟到数小时 | 普通事件分析确认 |
| `time_sensitive` | 短线机会，5 到 30 分钟可能失效 | 短线交易计划、盘中事件套利 |
| `urgent` | 需要立即响应 | 止损、减仓、撤单、重大突发风险 |

`expiration_action` 支持：

| 动作 | 含义 | 适用场景 |
| --- | --- | --- |
| `expire_reject` | 超时自动拒绝 | 加仓、开仓、提高杠杆 |
| `expire_approve` | 超时自动同意 | 用户明确配置的紧急止损、保本动作 |
| `expire_notify_only` | 超时只通知，不执行 | 普通分析、非关键建议 |
| `expire_reanalysis` | 超时后要求重分析 | 短线机会过期、行情已变化 |
| `execute_then_notify` | 立即执行并通知 | 用户预授权的止损、减仓、撤单 |
| `escalate` | 升级到更强确认方式 | 文本确认含糊、风险过高 |

### ApprovalInput

ApprovalInput 记录用户从某个通道给出的原始输入。

```text
ApprovalInput
  id
  approval_id
  channel
  actor_ref
  raw_text
  structured_payload
  received_at
```

`channel` 示例：

```text
web
approval_link
qq
wechat
telegram
discord
email
local_cli
```

规则：

- 文本通道输入不能直接等价于批准，必须经过 ApprovalEvaluation。
- 一次性授权 link 必须有过期时间、签名和目标 action 绑定。
- 所有原始输入必须进入 audit。
- 文本通道不得返回敏感交易细节，除非用户配置允许。

### ApprovalEvaluation

ApprovalEvaluation 将用户输入转成结构化判断。

```text
ApprovalEvaluation
  approval_id
  input_id
  evaluator_type
  interpreted_intent
  confidence
  extracted_changes
  requires_stronger_confirmation
  reason_summary
```

`evaluator_type` 支持：

```text
rule
llm
manual
```

规则：

- AI 可以判断用户是否表达同意、拒绝、修改参数、要求重分析或暂停。
- AI 判断置信度不足时必须升级为更强确认方式。
- 高风险交易请求即使 AI 判断同意，也可以要求一次性 link 或 Web 后台二次确认。
- 最终是否执行由 Policy Gate 决定。

### 动作策略示例

短线交易机会：

```text
action_type: execute_order
action_side: increase_risk
urgency: time_sensitive
expires_in: 5m
expiration_action: expire_reanalysis
required_confirmation_level: link_confirm
```

含义：5 分钟内用户可通过链接确认；超时后不能继续按原建议执行，必须重新分析。

紧急止损：

```text
action_type: reduce_position
action_side: reduce_risk
urgency: urgent
expires_in: 30s
expiration_action: expire_approve
required_confirmation_level: soft_confirm
policy_source: user_config
```

含义：用户预先配置允许紧急止损时，系统可以短暂等待人类响应；超时自动同意，执行后通知。

仅通知：

```text
action_type: notify
action_side: neutral
urgency: normal
expiration_action: expire_notify_only
required_confirmation_level: informational
```

含义：普通通知不需要审批。

## 运行时可观测 API

Agent、Tool、Skill 需要暴露运行摘要和审计摘要，但不暴露完整模型推理链。

建议资源：

```text
/agents/definitions
/agents/runs
/agents/runs/{run_id}/steps
/tools
/tools/invocations
/skills
```

规则：

- Agent run 需要展示状态、输入摘要、输出摘要、错误摘要和耗时。
- Tool invocation 需要展示工具 ID、参数摘要、结果摘要、耗时、错误和 trace_id。
- Skill 需要展示来源、版本、授权状态和被哪些 Agent 引用。
- 不保存或返回完整 chain-of-thought。
- Prompt、密钥、私有策略和敏感配置必须脱敏。

## 鉴权边界

初版采用本地单用户 token / session，不做完整 RBAC 和多租户。

原因：

- 插件配置、API key、HITL 授权、executor 能力都是敏感能力，不能完全裸奔；初版 executor 只做虚盘，不操作实盘。
- 当前阶段重点是插件、Agent、事件链路和审批策略，不适合先做复杂用户体系。
- 代码结构上保留 `actor`、`actor_type`、`permission`、`audit` 字段，后续可扩展 RBAC。

规则：

- 本地开发可通过配置关闭鉴权，但默认 Docker 部署应开启。
- 高风险动作必须记录 actor。
- ApprovalInput 的 actor 可以来自 Web session、一次性 link、消息通道账号或 local CLI。
- API 响应不得暴露 token、secret 或签名原文。

## 分页、过滤和排序

列表接口优先使用 cursor pagination。

示例：

```text
GET /events?limit=50&cursor=xxx&sort=-created_at&status=decision_ready
```

规则：

- `limit` 控制每页数量。
- `cursor` 用于翻页。
- `sort` 使用字段名，降序用 `-` 前缀。
- 常用筛选字段应显式建模，例如 `status`、`plugin_id`、`event_id`、`created_at`。
- 事件流、审计日志、Agent run、Tool invocation 使用 cursor pagination。
- 小型配置列表可以兼容 page / page_size，但不作为主规范。

## 初版 API 资源边界

初版不要求一次实现所有 endpoint，但资源边界按下面划分。

```text
/events
/raw-events
/events/{event_id}/state-transitions

/plugins
/plugins/{plugin_id}/config-schema
/plugins/{plugin_id}/config
/plugins/{plugin_id}/actions/install
/plugins/{plugin_id}/actions/enable
/plugins/{plugin_id}/actions/disable
/plugins/{plugin_id}/actions/reload

/source-bindings
/source-bindings/{binding_id}/actions/trigger
/scheduler/runs

/agents/definitions
/agents/runs
/agents/runs/{run_id}/steps

/tools
/tools/invocations

/skills

/industry-analyses
/scored-analyses
/decisions

/action-requests
/approval-policies
/approvals
/approvals/{approval_id}/actions/approve
/approvals/{approval_id}/actions/reject
/approvals/{approval_id}/actions/request_reanalysis
/approvals/{approval_id}/actions/amend
/approvals/{approval_id}/inputs
/approvals/{approval_id}/links
/approval-evaluations

/notifications

/executors
/executors/{executor_id}/actions/dry_run

/runtime/health
/runtime/errors
/audit-logs
```

## 初版落地顺序

建议按以下顺序实现，避免一次性铺太大：

1. 统一 `ApiResponse<T>`、错误码和 request_id / trace_id。
2. 事件、插件、Agent run、Tool invocation 的只读查询 API。
3. 插件配置 schema-driven API。
4. ApprovalRequest / ApprovalInput / ApprovalEvaluation / ApprovalDecision 数据模型和 API。
5. Native WebSocket topic 通知。
6. ApprovalPolicyResolver 与 `expires_at` / `expiration_action`。
7. 前端生成 client、types 和 Zod schema。
