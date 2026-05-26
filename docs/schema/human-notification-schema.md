# Human / Notification Schema 设计

## 设计依据

本文档根据 `docs/design/02-core-architecture-and-runtime.md`、
`docs/design/04-database-and-persistence-design.md`、`docs/design/08-api-and-websocket-design.md`
和 `docs/design/09-frontend-architecture-design.md` 收敛人工确认与通知相关数据库 schema。

Human / Notification 持久化目标：

- 记录 Decision / Policy Gate 产生的人工确认请求。
- 支持 Approval Inbox、Approval Detail、一次性授权 link、限时确认和 amend。
- 记录通知投递结果，UI 通知是初版必需能力，外部渠道作为插件预留。
- 外部通知失败不影响事件审计记录。
- 人工确认和通知结果必须可回放、可审计，并能与事件、Decision、工具调用串联。

初版包含两张表：

```text
approval_records
notification_records
```

本文档不单独拆 `approval_inputs` 或 `approval_evaluations` 表；初版将原始输入摘要、结构化解释和 amend 信息作为
JSONB 字段保存在 `approval_records`。如果后续需要多轮对话式审批，再拆分子表。

## 表关系

```text
events 1 ── 0..n approval_records
decision_results 1 ── 0..n approval_records
events 1 ── 0..n notification_records
decision_results 1 ── 0..n notification_records
approval_records 1 ── 0..n notification_records
```

- `approval_records` 记录一次人工确认请求及其最终结果。
- `notification_records` 记录一次通知投递请求及其发送结果。
- 通知可以来自 Decision，也可以来自 Approval 状态变化。

## 枚举与状态

### `approval_status`

| 值 | 说明 |
| --- | --- |
| `pending` | 等待用户处理 |
| `approved` | 用户已批准 |
| `rejected` | 用户已拒绝 |
| `reanalysis_requested` | 用户要求重新分析 |
| `amended` | 用户修改了请求参数并提交 |
| `expired` | 请求已过期 |
| `executed_then_notified` | 按策略先执行后通知 |
| `blocked` | Policy Gate 或系统底线阻断 |
| `canceled` | 系统、用户或调度器取消 |
| `failed` | 审批流程处理失败 |

### `approval_action`

| 值 | 说明 |
| --- | --- |
| `approve` | 批准原请求 |
| `reject` | 拒绝原请求 |
| `request_reanalysis` | 要求重新分析 |
| `amend` | 修改请求参数后提交 |
| `cancel` | 取消请求 |

### `confirmation_level`

| 值 | 说明 |
| --- | --- |
| `informational` | 只通知，不需要确认 |
| `soft_confirm` | 文本同意可以接受 |
| `strong_confirm` | 需要明确结构化确认 |
| `link_confirm` | 需要一次性链接确认 |
| `manual_only` | 只能 Web 后台或本地控制台确认 |

### `action_side`

| 值 | 说明 |
| --- | --- |
| `increase_risk` | 增加风险，例如开仓、加仓、提高杠杆 |
| `reduce_risk` | 降低风险，例如止损、减仓、撤单 |
| `neutral` | 中性动作，例如通知、继续分析 |

### `approval_urgency`

| 值 | 说明 |
| --- | --- |
| `low` | 不敏感，小时级有效 |
| `normal` | 常规时效，几十分钟到数小时 |
| `time_sensitive` | 短线机会，通常 5 到 30 分钟可能失效 |
| `urgent` | 需要立即响应 |

### `expiration_action`

| 值 | 说明 |
| --- | --- |
| `expire_reject` | 超时自动拒绝 |
| `expire_approve` | 超时自动同意，仅适合用户预授权的降风险动作 |
| `expire_notify_only` | 超时后只通知，不执行 |
| `expire_reanalysis` | 超时后要求重新分析 |
| `execute_then_notify` | 立即执行并通知 |
| `escalate` | 升级到更强确认方式 |

### `notification_status`

| 值 | 说明 |
| --- | --- |
| `pending` | 通知已创建但尚未发送 |
| `sending` | 正在发送 |
| `sent` | 已发送到目标渠道 |
| `delivered` | 目标渠道确认送达 |
| `failed` | 发送失败 |
| `canceled` | 发送被取消 |
| `skipped` | 策略判断无需发送 |

### `notification_channel`

| 值 | 说明 |
| --- | --- |
| `ui` | UI 内通知，初版必需 |
| `approval_link` | 一次性授权链接通知 |
| `telegram` | Telegram 通知插件 |
| `discord` | Discord 通知插件 |
| `email` | Email 通知插件 |
| `webhook` | Webhook 通知插件 |
| `local_cli` | 本地 CLI 通知 |

### `approval_input_channel`

| 值 | 说明 |
| --- | --- |
| `web` | Web 管理台输入 |
| `approval_link` | 一次性授权链接输入 |
| `qq` | QQ 文本输入 |
| `wechat` | 微信文本输入 |
| `telegram` | Telegram 文本输入 |
| `discord` | Discord 文本输入 |
| `email` | Email 输入 |
| `local_cli` | 本地 CLI 输入 |

## `approval_records`

### 用途

`approval_records` 记录系统需要人类介入、等待限时确认或执行后通知的请求。它支撑 Approval Inbox、Approval Detail、
一次性授权链接和后续审计。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 人工确认记录 ID |
| `event_id` | `uuid` | not null, foreign key | 关联事件 ID |
| `decision_result_id` | `uuid` | nullable, foreign key | 触发该审批的 Decision 结果 ID |
| `tool_invocation_id` | `uuid` | nullable, foreign key | 触发该审批的高风险工具调用 ID |
| `target_type` | `text` | not null | 审批目标类型，例如 `decision`、`tool_invocation`、`broker_action`、`plugin_config` |
| `target_id` | `text` | not null | 审批目标 ID，使用 text 以兼容不同目标表 |
| `action_type` | `text` | not null | 请求动作类型，例如 `notify`、`monitor`、`dry_run`、`execute_order`、`reduce_position`；`dry_run` 表示虚盘，不操作实盘 |
| `action_side` | `text` | not null | 风险方向，按 `action_side` 值约束，用于前端风险提示和 Policy Gate |
| `risk_level` | `text` | not null | 风险等级，建议值为 `low`、`medium`、`high`、`critical` |
| `urgency` | `text` | not null | 时效等级，按 `approval_urgency` 值约束 |
| `summary` | `text` | not null | 给用户展示的审批摘要 |
| `proposed_payload` | `jsonb` | not null, default `{}` | 拟执行动作的结构化摘要，不能包含 secret 或敏感账户明细 |
| `amended_payload` | `jsonb` | nullable | 用户 amend 后的结构化参数 |
| `required_confirmation_level` | `text` | not null | 所需确认强度，按 `confirmation_level` 值约束 |
| `expiration_action` | `text` | not null | 超时后的系统动作，按 `expiration_action` 值约束 |
| `policy_source` | `text` | nullable | 审批策略来源，例如 `system_default`、`user_config`、`strategy_policy` |
| `policy_snapshot` | `jsonb` | not null, default `{}` | 策略解析摘要，不保存私有策略全文或 secret |
| `status` | `text` | not null | 当前审批状态，按 `approval_status` 值约束 |
| `final_action` | `text` | nullable | 用户最终动作，按 `approval_action` 值约束；超时或阻断时可以为空 |
| `input_channel` | `text` | nullable | 用户输入来源渠道，按 `approval_input_channel` 值约束 |
| `input_summary` | `jsonb` | nullable | 用户原始输入的脱敏摘要，不保存敏感交易细节原文 |
| `evaluation_summary` | `jsonb` | nullable | ApprovalEvaluation 结构化摘要，包括 evaluator、intent、confidence、extracted_changes |
| `requires_stronger_confirmation` | `boolean` | not null, default `false` | 用户输入是否需要升级到更强确认方式 |
| `approval_token_hash` | `text` | nullable | 一次性授权 link token 的 hash，不保存 token 原文 |
| `approval_token_expires_at` | `timestamptz` | nullable | 一次性授权 link 过期时间 |
| `expires_at` | `timestamptz` | nullable | 审批请求过期时间 |
| `resolved_at` | `timestamptz` | nullable | 审批最终完成、过期、取消或阻断时间 |
| `actor_type` | `text` | nullable | 处理审批的 actor 类型，例如 `user`、`system`、`policy` |
| `actor_id` | `text` | nullable | 处理审批的 actor ID 或系统模块名 |
| `request_id` | `text` | nullable | 处理审批的 HTTP 请求 ID 或任务 ID |
| `trace_id` | `text` | not null | 跨事件、Decision、通知和审计的追踪 ID |
| `error_code` | `text` | nullable | 审批流程失败时的结构化错误码 |
| `error_message` | `text` | nullable | 审批流程失败时的脱敏错误摘要 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、私有策略或敏感工具参数 |
| `created_at` | `timestamptz` | not null, default `now()` | 记录创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 记录最近更新时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `decision_result_id` 外键引用 `decision_results.id`，建议 `on delete set null`。
- `tool_invocation_id` 外键引用 `tool_invocations.id`，建议 `on delete set null`。
- `index(status, expires_at asc)`，支持 Approval Inbox 优先展示待处理和即将过期记录。
- `index(event_id, created_at desc)`，支持按事件回放审批记录。
- `index(decision_result_id)`，支持从 Decision 回查审批。
- `index(target_type, target_id)`，支持按审批目标查询。
- `index(actor_type, actor_id)`，支持按操作者查询。
- `partial unique index(approval_token_hash) where approval_token_hash is not null`，支持一次性授权 link 校验，并确保单个 token hash 只映射一条审批记录。
- `index(trace_id)`，支持跨表追踪。

### 写入规则

- 用户拒绝后，不允许同一 Decision 继续进入 broker。
- 文本通道输入不能直接等价于批准，必须经过 `evaluation_summary` 或更强确认流程。
- 一次性授权 link 只保存 token hash，必须绑定目标 action、过期时间和风险摘要。
- 一次性授权 token hash 必须唯一映射到单条审批记录，不允许复用。
- `execute_then_notify` 必须记录为 `executed_then_notified`，不能伪装成待审批。
- 人工确认不能绕过系统级风险限制；Policy Gate 可以将请求记为 `blocked`。
- Approval 处理结果应在同一业务事务内更新事件状态，并追加事件状态流转记录。

## `notification_records`

### 用途

`notification_records` 记录 UI 或外部渠道的一次通知投递请求和结果。通知可以来自 Decision、Approval、运行时错误或插件事件。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 通知记录 ID |
| `event_id` | `uuid` | nullable, foreign key | 关联事件 ID；非事件类系统通知可以为空 |
| `decision_result_id` | `uuid` | nullable, foreign key | 触发通知的 Decision 结果 ID |
| `approval_record_id` | `uuid` | nullable, foreign key | 触发通知的审批记录 ID |
| `channel` | `text` | not null | 通知渠道，按 `notification_channel` 值约束；UI 是初版必需渠道 |
| `provider_plugin_id` | `text` | nullable | 提供外部通知能力的插件 ID；UI 内通知可为空 |
| `provider_plugin_version` | `text` | nullable | 通知插件版本 |
| `recipient_type` | `text` | nullable | 接收者类型，例如 `user`、`channel`、`webhook`、`local_admin` |
| `recipient_ref` | `text` | nullable | 接收者引用，必须脱敏，不能保存完整 token、邮箱密文以外敏感值 |
| `title` | `text` | not null | 通知标题 |
| `body_summary` | `text` | nullable | 通知正文摘要，不保存敏感交易细节或 secret |
| `payload` | `jsonb` | not null, default `{}` | 发送 payload 的脱敏结构化摘要 |
| `status` | `text` | not null | 通知发送状态，按 `notification_status` 值约束 |
| `priority` | `text` | not null, default `normal` | 通知优先级，建议值为 `low`、`normal`、`high`、`urgent` |
| `dedupe_key` | `text` | nullable | 通知去重 key，避免重复发送同一提醒 |
| `external_message_id` | `text` | nullable | 外部渠道返回的消息 ID |
| `scheduled_at` | `timestamptz` | nullable | 计划发送时间 |
| `sent_at` | `timestamptz` | nullable | 实际发送时间 |
| `delivered_at` | `timestamptz` | nullable | 外部渠道确认送达时间 |
| `failed_at` | `timestamptz` | nullable | 发送失败时间 |
| `retry_count` | `integer` | not null, default `0` | 已重试次数 |
| `next_retry_at` | `timestamptz` | nullable | 下一次重试时间 |
| `trace_id` | `text` | not null | 跨事件、Decision、Approval 和审计的追踪 ID |
| `error_code` | `text` | nullable | 发送失败的结构化错误码 |
| `error_message` | `text` | nullable | 发送失败的脱敏错误摘要 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、真实 webhook token 或敏感工具参数 |
| `created_at` | `timestamptz` | not null, default `now()` | 记录创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 记录最近更新时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `decision_result_id` 外键引用 `decision_results.id`，建议 `on delete set null`。
- `approval_record_id` 外键引用 `approval_records.id`，建议 `on delete set null`。
- 通知与 runtime error 的关联由 `runtime_errors.notification_record_id` 或 `trace_id` 表达，本表不反向保存 `runtime_error_id`，避免双向 nullable 关系漂移。
- `index(channel, status)`，支持按渠道排查通知状态。
- `index(status, scheduled_at asc)`，支持发送队列读取。
- `index(event_id, created_at desc)`，支持事件轨迹回放。
- `index(decision_result_id)`，支持从 Decision 回查通知。
- `index(approval_record_id)`，支持从 Approval 回查通知。
- `index(dedupe_key)`，支持通知去重。
- `index(trace_id)`，支持跨表追踪。

### 写入规则

- UI 内通知是初版必需能力。
- Discord、Telegram、Email、Webhook 等外部渠道通过 notification plugin 扩展。
- 外部通知失败不应影响事件、Decision 或 Approval 的审计记录写入。
- 通知 payload 必须脱敏，不保存 secret、完整 webhook token、私有策略或敏感交易明细。
- 发送失败应记录 `status = failed`、错误摘要和重试信息。

## 验证建议

落地 ORM model 和 Alembic migration 时，至少验证：

- 空库 upgrade 后包含 `approval_records`、`notification_records`、枚举、外键和关键索引。
- Approval Inbox 可以按 `status` 和 `expires_at` 查询待处理、即将过期和已处理记录。
- 一次性授权 link 只保存 token hash，不保存 token 原文。
- `approve`、`reject`、`request_reanalysis`、`amend` 都能落到结构化字段。
- `execute_then_notify` 不会显示成待审批。
- 外部通知失败不会阻断事件状态、Decision 或 Approval 记录写入。
- payload、input summary、error message 不暴露 secret 或敏感交易细节原文。

## 后续扩展

- 如果审批需要多轮自然语言对话，可拆分 `approval_inputs` 和 `approval_evaluations` 子表。
- 如果通知队列需要更强可靠性，可增加 outbox 或 delivery attempt 明细表。
- 如果一次性授权 link 面向外部网络暴露，需要补充 token 签名、设备指纹、IP 限流和风控记录。
- 统一 `audit_logs` 落地后，Approval 创建、处理、过期、amend、通知发送成功或失败都应写 audit。
