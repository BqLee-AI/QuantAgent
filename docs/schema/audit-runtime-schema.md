# Audit / Runtime Schema 设计

## 设计依据

本文档根据 `docs/design/04-database-and-persistence-design.md`、`docs/design/08-api-and-websocket-design.md`
和 API 鉴权设计中的 actor/audit context 边界，收敛 Audit / Runtime 相关数据库 schema。

Audit / Runtime 持久化目标：

- 以 append-only 方式记录关键业务动作，支持回放、排查和审计。
- 记录运行时错误摘要，支持 Runtime 页面、告警、问题定位和后续通知。
- 对同一个业务动作，主表更新与 audit 写入应在同一事务边界内完成。
- 不保存 secret、cookie、session、签名、口令、数据库连接串、完整 stack trace 或完整敏感载荷。

初版包含两张表：

```text
audit_logs
runtime_errors
```

## 表关系

```text
audit_logs -> 任意业务对象
runtime_errors -> 任意运行时组件
runtime_errors 0..1 ── 0..n audit_logs
```

- `audit_logs` 是统一审计流水，不替代各主表当前状态。
- `runtime_errors` 是运行时错误摘要表，用于错误查询、告警和排查。
- 业务主表保存当前状态，审计表保存历史变化。

## 枚举与状态

### `audit_action` 命名

`audit_logs.action` 初版建议使用 `text`，不使用 PostgreSQL enum。审计动作会随业务增长扩展，
用文本命名可以减少 migration 成本。命名建议采用 `<domain>.<action>`：

| 值 | 说明 |
| --- | --- |
| `event.state_changed` | Event 状态变化 |
| `plugin.installed` | 插件安装 |
| `plugin.upgraded` | 插件升级 |
| `plugin.downgraded` | 插件降级 |
| `plugin.enabled` | 插件启用 |
| `plugin.disabled` | 插件停用 |
| `plugin.reloaded` | 插件 reload |
| `plugin.uninstalled` | 插件卸载 |
| `plugin.config_changed` | 插件配置变更 |
| `plugin.dependency_installed` | 插件依赖自动安装 |
| `decision.created` | Decision 生成 |
| `approval.resolved` | Human Approval 被确认、拒绝或要求重分析 |
| `notification.sent` | 通知发送成功 |
| `notification.failed` | 通知发送失败 |
| `tool.invoked` | 工具调用 |
| `runtime.error_recorded` | 运行时错误被记录 |

### `audit_outcome`

| 值 | 说明 |
| --- | --- |
| `succeeded` | 动作成功 |
| `failed` | 动作失败 |
| `blocked` | 动作被权限、策略或风险门禁阻断 |
| `canceled` | 动作被取消 |
| `expired` | 动作超时或过期 |

### `runtime_error_status`

| 值 | 说明 |
| --- | --- |
| `open` | 错误仍需关注 |
| `acknowledged` | 错误已被确认 |
| `resolved` | 错误已解决 |
| `ignored` | 错误被标记为无需处理 |

### `runtime_error_severity`

| 值 | 说明 |
| --- | --- |
| `info` | 信息级异常或可忽略问题 |
| `warning` | 警告，功能可能降级 |
| `error` | 错误，某个流程失败 |
| `critical` | 严重错误，可能影响关键运行闭环 |

### `runtime_component`

| 值 | 说明 |
| --- | --- |
| `api` | FastAPI HTTP 边界 |
| `worker` | worker 任务或后台流程 |
| `scheduler` | 调度器 |
| `event_bus` | Event Bus |
| `plugin_registry` | 插件 Registry |
| `plugin` | 具体插件运行 |
| `agent_runtime` | AgentRuntime |
| `tool_registry` | ToolRegistry |
| `decision` | Decision / Policy Gate |
| `notification` | 通知模块或通知插件 |
| `approval` | Human Approval 流程 |
| `executor` | executor 或虚盘流程；虚盘对应协议值 `dry_run` |
| `database` | 数据库连接、session 或 migration |

## `audit_logs`

### 用途

`audit_logs` 以 append-only 方式记录关键业务动作。它用于历史回放、合规排查、问题定位和 PR/运维证据链，不作为业务当前状态真源。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 审计记录 ID |
| `action` | `text` | not null | 审计动作类型，按 `<domain>.<action>` 命名 |
| `outcome` | `text` | not null | 动作结果，按 `audit_outcome` 值约束 |
| `target_type` | `text` | not null | 被审计对象类型，例如 `event`、`plugin`、`decision`、`approval`、`notification` |
| `target_id` | `text` | not null | 被审计对象 ID，使用 text 以兼容不同业务表 |
| `event_id` | `uuid` | nullable, foreign key | 关联事件 ID；非事件类审计可为空 |
| `actor_type` | `text` | not null | 触发动作的 actor 类型，例如 `user`、`system`、`plugin`、`agent`、`scheduler` |
| `actor_id` | `text` | not null | 触发动作的 actor ID、插件 ID、agent ID 或系统模块名 |
| `capabilities` | `jsonb` | not null, default `[]` | 动作发生时 actor 的 capability 快照 |
| `request_id` | `text` | nullable | HTTP 请求 ID 或后台任务请求 ID |
| `trace_id` | `text` | not null | 跨事件、Agent、工具、Decision 和通知的追踪 ID |
| `correlation_id` | `text` | nullable | 与 Event Envelope 或上游任务关联的 correlation ID |
| `causation_id` | `text` | nullable | 引发该动作的上游动作 ID |
| `source_component` | `text` | nullable | 触发审计的系统组件，按 `runtime_component` 值约束 |
| `source_plugin_id` | `text` | nullable | 触发审计的插件 ID |
| `source_plugin_version` | `text` | nullable | 触发审计的插件版本 |
| `summary` | `text` | not null | 审计摘要，供 UI 和排查阅读 |
| `reason` | `text` | nullable | 动作原因摘要 |
| `before_state` | `jsonb` | nullable | 动作前状态的脱敏摘要 |
| `after_state` | `jsonb` | nullable | 动作后状态的脱敏摘要 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、cookie、session、私有策略全文或敏感载荷 |
| `runtime_error_id` | `uuid` | nullable, foreign key | 关联运行时错误 ID |
| `error_code` | `text` | nullable | 动作失败、阻断或错误时的结构化错误码 |
| `error_message` | `text` | nullable | 脱敏错误摘要，不保存 stack trace、连接串或 secret |
| `occurred_at` | `timestamptz` | not null, default `now()` | 动作发生时间 |
| `created_at` | `timestamptz` | not null, default `now()` | 审计记录写入时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`。
- `runtime_error_id` 外键引用 `runtime_errors.id`，建议 `on delete set null`。
- `index(target_type, target_id, occurred_at desc)`，支持按对象回放审计历史。
- `index(event_id, occurred_at desc)`，支持按事件回放审计链。
- `index(action, occurred_at desc)`，支持按动作类型查询。
- `index(outcome, occurred_at desc)`，支持排查失败、阻断、过期动作。
- `index(actor_type, actor_id, occurred_at desc)`，支持按操作者或模块查询。
- `index(request_id)`，支持按 HTTP 请求或任务追踪。
- `index(trace_id)`，支持跨表追踪。
- `index(correlation_id)`，支持按上游任务追踪。

### 写入规则

- `audit_logs` 只追加，不更新、不删除业务历史。
- 主表用于查询当前状态，审计表用于回放历史变化。
- 对同一个业务动作，写主表和写 audit 应在同一事务边界内完成。
- 审计摘要必须脱敏，不保存 secret、cookie、session、签名、口令、完整模型推理链或敏感工具参数。
- 如果动作失败但主表无需更新，仍可以写入失败 audit，用于排查。

## `runtime_errors`

### 用途

`runtime_errors` 记录运行时错误摘要，用于 Runtime 页面、告警、通知、排查和后续审计串联。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 运行时错误记录 ID |
| `component` | `text` | not null | 发生错误的系统组件，按 `runtime_component` 值约束 |
| `severity` | `text` | not null | 错误严重级别，按 `runtime_error_severity` 值约束 |
| `status` | `text` | not null | 错误处理状态，按 `runtime_error_status` 值约束 |
| `error_code` | `text` | not null | 结构化错误码 |
| `error_message` | `text` | not null | 脱敏错误摘要 |
| `error_class` | `text` | nullable | 异常类型名或错误类别，不包含完整 stack trace |
| `event_id` | `uuid` | nullable, foreign key | 关联事件 ID |
| `plugin_id` | `text` | nullable | 关联插件 ID |
| `plugin_version` | `text` | nullable | 关联插件版本 |
| `agent_run_id` | `uuid` | nullable, foreign key | 关联 Agent run ID |
| `tool_invocation_id` | `uuid` | nullable, foreign key | 关联工具调用 ID |
| `decision_result_id` | `uuid` | nullable, foreign key | 关联 Decision 结果 ID |
| `approval_record_id` | `uuid` | nullable, foreign key | 关联 Approval 记录 ID |
| `notification_record_id` | `uuid` | nullable, foreign key | 关联 Notification 记录 ID |
| `request_id` | `text` | nullable | HTTP 请求 ID 或后台任务请求 ID |
| `trace_id` | `text` | not null | 跨表追踪 ID |
| `correlation_id` | `text` | nullable | 与上游任务或 Event Envelope 关联的 correlation ID |
| `operation` | `text` | nullable | 发生错误的操作名，例如 `plugin.start`、`tool.invoke`、`decision.create` |
| `retryable` | `boolean` | not null, default `false` | 错误是否可重试 |
| `retry_count` | `integer` | not null, default `0` | 已重试次数 |
| `next_retry_at` | `timestamptz` | nullable | 下一次重试时间 |
| `first_seen_at` | `timestamptz` | not null, default `now()` | 首次发现时间 |
| `last_seen_at` | `timestamptz` | not null, default `now()` | 最近一次发现时间 |
| `occurrence_count` | `integer` | not null, default `1` | 相同错误聚合出现次数 |
| `acknowledged_at` | `timestamptz` | nullable | 错误被确认时间 |
| `acknowledged_by_type` | `text` | nullable | 确认错误的 actor 类型 |
| `acknowledged_by` | `text` | nullable | 确认错误的 actor ID 或模块名 |
| `resolved_at` | `timestamptz` | nullable | 错误解决时间 |
| `resolution_summary` | `text` | nullable | 错误解决摘要 |
| `context_summary` | `jsonb` | not null, default `{}` | 脱敏上下文摘要，不保存完整请求体、响应体或敏感工具参数 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、连接串、cookie、session 或完整 stack trace |
| `created_at` | `timestamptz` | not null, default `now()` | 记录创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 记录最近更新时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete set null`。
- `agent_run_id` 外键引用 `agent_runs.id`，建议 `on delete set null`。
- `tool_invocation_id` 外键引用 `tool_invocations.id`，建议 `on delete set null`。
- `decision_result_id` 外键引用 `decision_results.id`，建议 `on delete set null`。
- `approval_record_id` 外键引用 `approval_records.id`，建议 `on delete set null`。
- `notification_record_id` 外键引用 `notification_records.id`，建议 `on delete set null`。
- `index(component, status, severity)`，支持 Runtime 页面筛选。
- `index(error_code, last_seen_at desc)`，支持错误聚合和排查。
- `index(status, last_seen_at desc)`，支持查看未处理错误。
- `index(event_id, last_seen_at desc)`，支持按事件排查错误。
- `index(plugin_id, plugin_version)`，支持按插件排查错误。
- `index(request_id)`，支持按请求追踪。
- `index(trace_id)`，支持跨表追踪。
- `index(correlation_id)`，支持按上游任务追踪。

### 写入规则

- 运行时错误记录必须脱敏，不能保存完整 stack trace、secret、cookie、session、口令、连接串或完整敏感载荷。
- 相同错误可以按 `component + error_code + trace_id` 或后续更稳定 key 聚合，更新 `last_seen_at` 和 `occurrence_count`。
- 关键错误应在同一事务内先写入 `runtime_errors`，再写入 `audit_logs(action = runtime.error_recorded, runtime_error_id = <id>)`。如果 `runtime_errors` 写入失败，不应递归创建新的 runtime error。
- 如果错误来自外部通知失败，记录错误不能阻断事件、Decision 或 Approval 的主流程记录。

## 必须写审计的动作

以下动作必须写入 `audit_logs`：

- Event 状态变化。
- 插件安装、升级、降级、启用、停用、reload、卸载。
- 插件配置变更。
- 插件依赖自动安装、失败或阻塞。
- Decision 生成。
- Human Approval 确认、拒绝、要求重分析、amend、过期或阻断。
- Notification 发送成功、失败、跳过或取消。
- 高风险 Tool invocation 成功、失败或被阻断。
- Runtime error。

## 验证建议

落地 ORM model 和 Alembic migration 时，至少验证：

- 空库 upgrade 后包含 `audit_logs`、`runtime_errors`、必要枚举或 check constraint、外键和关键索引。
- `audit_logs` 只追加，不提供业务更新或删除路径。
- 同一业务动作能在主表更新和 audit 写入的同一事务内完成。
- actor/audit context 不包含 session、cookie、signature、password、hash 或 secret。
- 错误响应和 runtime error 不暴露连接串、stack trace、secret 或敏感载荷。
- Runtime error 可以按 component、status、severity、trace_id 查询。
- Notification 失败和 runtime error 记录不会破坏原业务状态写入。

## 后续扩展

- 生产归档策略、保留周期和物理删除策略后续单独设计。
- 如果需要不可篡改审计，可增加 hash chain、签名或外部 WORM 存储。
- 如果运行时错误需要完整调试详情，应接入外部 observability 系统，只在数据库保存 trace reference 和脱敏摘要。
- 如果告警需要更强可靠性，可增加 alert/outbox 表。
