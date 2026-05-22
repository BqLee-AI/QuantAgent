# Event Schema 设计

## 设计依据

本文档根据 `docs/design/02-core-architecture-and-runtime.md` 和
`docs/design/04-database-and-persistence-design.md` 收敛 Event 相关数据库 schema。

Event 是 QuantAgent 运行时主对象。初版持久化采用三层结构：

```text
raw_events
events
event_state_transitions
```

设计目标：

- 保留 source 插件采集到的原始输入，支持标准化回放和排查。
- 保存标准化后的主事件对象，作为 Router Agent、Industry Plugin、Decision 和 UI 的输入。
- 以 append-only 方式记录事件状态流转，避免只依赖当前状态导致历史不可回放。
- 核心查询字段结构化保存，演进字段使用 JSONB 承载。
- ORM model 只作为数据库映射，不直接作为 API DTO、Event DTO 或 Plugin DTO 返回。

## 表关系

```text
raw_events 1 ── 0..n events 1 ── 1..n event_state_transitions
```

- `raw_events` 保存原始输入。
- `events` 保存标准化事件和当前状态。
- `event_state_transitions` 保存事件状态历史。
- 手工录入或内部生成事件可以没有 `raw_event_id`。

## `raw_events`

### 用途

保存 source 插件采集到的原始输入，例如 RSS、URL、X API、Webhook、Readability/Jina
link reader 等不同 source 的原始载荷。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 原始事件 ID |
| `source_plugin_id` | `text` | not null | 采集插件 ID |
| `source_plugin_version` | `text` | nullable | 采集插件版本 |
| `source_type` | `text` | not null | 来源类型，如 `rss`、`url`、`x_api`、`webhook`、`manual` |
| `external_id` | `text` | nullable | 外部系统原始 ID |
| `url` | `text` | nullable | 原始链接 |
| `title` | `text` | nullable | 原始标题，便于排查 |
| `payload` | `jsonb` | not null | 原始载荷 |
| `payload_hash` | `text` | not null | 原始载荷稳定 hash |
| `captured_at` | `timestamptz` | not null | source 采集时间 |
| `ingested_at` | `timestamptz` | not null, default `now()` | 入库时间 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息 |

### 约束与索引

- `unique(source_plugin_id, payload_hash)`，避免同一 source 重复写入相同原始载荷。
- `index(captured_at desc)`，支持按采集时间读取。
- `index(source_plugin_id, captured_at desc)`，支持按插件查看采集历史。
- `index(source_type, captured_at desc)`，支持按来源类型筛选。

### 写入规则

- `payload_hash` 应使用 canonical JSON 或原始字节稳定序列化后计算，避免相同载荷因字段顺序不同重复入库。
- `payload` 不保存 secret、token、私有策略或完整敏感工具参数。
- 初版不为 `payload` 加 GIN 索引，等查询路径稳定后再补。

## `events`

### 用途

保存系统标准化后的主事件对象，供 Router Agent、Industry Plugin、Decision、Notification
和 UI 使用。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 标准事件 ID |
| `raw_event_id` | `uuid` | nullable, foreign key | 来源原始事件 ID |
| `source` | `text` | not null | 标准化来源名称，如 `sec-rss`、`manual` |
| `source_type` | `text` | not null | 来源类型 |
| `title` | `text` | not null | 标准化标题 |
| `content` | `text` | nullable | 标准化正文或摘要正文 |
| `url` | `text` | nullable | 标准化 URL |
| `published_at` | `timestamptz` | nullable | 外部发布时间 |
| `captured_at` | `timestamptz` | not null | 系统采集时间 |
| `language` | `text` | nullable | 语言，如 `zh`、`en` |
| `entities` | `jsonb` | not null, default `[]` | 结构化实体数组 |
| `tags` | `jsonb` | not null, default `[]` | 标签数组 |
| `status` | `event_status` | not null | 当前事件状态 |
| `trace_id` | `text` | not null | 贯穿事件管线的 trace ID |
| `correlation_id` | `text` | nullable | Event Envelope correlation ID |
| `causation_id` | `text` | nullable | Event Envelope causation ID |
| `metadata` | `jsonb` | not null, default `{}` | 扩展 metadata |
| `deleted_at` | `timestamptz` | nullable | 软删除时间；为空表示事件仍处于可见主流程 |
| `deleted_by_type` | `text` | nullable | 执行软删除的 actor 类型，例如 `user`、`system` |
| `deleted_by` | `text` | nullable | 执行软删除的 actor ID 或系统模块名 |
| `deleted_reason` | `text` | nullable | 软删除原因摘要，必须脱敏 |
| `created_at` | `timestamptz` | not null, default `now()` | 创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 更新时间 |

### `event_status`

初版状态枚举与运行时设计保持一致：

```text
captured
routed
analyzing
scored
decision_ready
pending_approval
approved
rejected
notified
dry_run_executed
failed
```

### 约束与索引

- `raw_event_id` 外键引用 `raw_events.id`，建议 `on delete set null`，避免原始事件清理破坏主事件历史。
- `index(status, captured_at desc)`，支持事件工作台按状态读取。
- `index(source, captured_at desc)`，支持按来源读取。
- `index(published_at desc)`，支持按外部发布时间读取。
- `index(trace_id)`，支持跨表追踪。
- `index(raw_event_id)`，支持从原始事件回查标准事件。
- `index(deleted_at)`，支持管理台筛选软删除事件。

### 写入规则

- 创建标准事件时，必须在同一事务内写入 `events.status = captured` 和第一条
  `event_state_transitions.to_status = captured`。
- `events.status` 只表示当前状态，历史以 `event_state_transitions` 为准。
- 删除事件采用 soft delete，只设置 `deleted_at`、`deleted_by_type`、`deleted_by` 和 `deleted_reason`；不得删除事件状态流转、审计、分析、审批或通知历史。
- 不建议初版设置全局 `unique(source, url)`，因为 URL 为空、canonical 规则不稳定或多 source
  转载同一链接时容易误伤。需要去重时优先使用 `raw_events.payload_hash` 或后续专门去重策略。

## `event_state_transitions`

### 用途

以 append-only 方式记录事件从 `captured` 到后续状态的全过程，用于审计、回放、排查和
UI 轨迹展示。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 状态流转记录 ID |
| `event_id` | `uuid` | not null, foreign key | 关联事件 ID |
| `from_status` | `event_status` | nullable | 初始记录可为空 |
| `to_status` | `event_status` | not null | 目标状态 |
| `transitioned_at` | `timestamptz` | not null, default `now()` | 状态变化时间 |
| `triggered_by_type` | `text` | not null | 触发者类型，如 `system`、`plugin`、`agent`、`user` |
| `triggered_by` | `text` | not null | 模块名、插件 ID、agent ID 或 actor ID |
| `actor_type` | `text` | nullable | 鉴权上下文中的 actor 类型 |
| `actor_id` | `text` | nullable | 鉴权上下文中的 actor ID |
| `request_id` | `text` | nullable | HTTP 或任务请求 ID |
| `reason` | `text` | nullable | 状态变化原因 |
| `error_code` | `text` | nullable | 失败时的错误码 |
| `error_message` | `text` | nullable | 脱敏错误摘要 |
| `trace_id` | `text` | not null | 跨表追踪 ID |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息 |
| `created_at` | `timestamptz` | not null, default `now()` | 写入时间 |

### 约束与索引

- `event_id` 外键引用 `events.id`，建议 `on delete restrict`，避免删除事件导致审计链断裂。
- `index(event_id, transitioned_at asc)`，支持读取单个事件完整轨迹。
- `index(to_status, transitioned_at desc)`，支持按状态变化查看运行情况。
- `index(triggered_by_type, triggered_by)`，支持按触发模块排查。
- `index(actor_type, actor_id)`，支持按操作者排查。
- `index(request_id)`，支持按请求追踪。
- `index(trace_id)`，支持跨表追踪。

### 写入规则

- 该表只追加，不更新、不删除业务历史。
- 每次状态变化必须同一事务内更新 `events.status`、`events.updated_at`，并追加一条 transition。
- `from_status` 应记录状态变化前的 `events.status`；初始 `captured` 记录可以为空。
- 错误信息必须脱敏，不保存 secret、token、完整模型推理链或敏感工具参数。

## 状态流转规则

推荐初版主路径：

```text
captured
  -> routed
  -> analyzing
  -> scored
  -> decision_ready
  -> pending_approval
  -> approved
  -> notified
  -> dry_run_executed
```

其他允许路径：

- 任意处理中状态可以转为 `failed`，但必须记录 `reason`、`error_code` 或 `error_message`。
- `pending_approval` 可以转为 `approved` 或 `rejected`。
- `decision_ready` 可以直接转为 `notified`，用于 `notify_only` 决策。

约束：

- 插件不能随意跳过 Decision 阶段。
- 实盘交易执行状态暂不进入初版主路径；虚盘状态继续使用协议值 `dry_run_executed`。
- 数据库层只保证引用完整性和历史可回放；合法状态跳转由 core repository 或 service 控制。

## 与 Event Envelope 的对应

Event Bus 传递的 Event Envelope 字段与数据库字段建议对应如下：

| Event Envelope | 数据库字段 |
| --- | --- |
| `event.id` | `events.id` |
| `topic` | `event_state_transitions.metadata.topic` 或后续消息表 |
| `correlation_id` | `events.correlation_id` |
| `causation_id` | `events.causation_id` |
| `producer` | `event_state_transitions.triggered_by` |
| `created_at` | `event_state_transitions.transitioned_at` |
| `retry_count` | `event_state_transitions.metadata.retry_count` |
| `headers` | `event_state_transitions.metadata.headers` |

初版不单独设计 Event Bus 消息持久化表；如果后续从进程内 Event Bus 迁移到 Redis Streams
或独立 outbox，再单独补充消息 schema。

## 验证建议

落地 ORM model 和 Alembic migration 时，至少验证：

- 空库 upgrade 后包含 `raw_events`、`events`、`event_state_transitions` 和 `event_status`。
- 外键、唯一约束和索引存在。
- 创建标准事件时会同时写入 `events` 和初始 transition。
- 状态变化会更新 `events.status` 并追加 transition，不覆盖历史 transition。
- 同一 `source_plugin_id + payload_hash` 重复写入 raw event 会失败或走幂等路径。
- 错误信息、metadata 和 payload 不暴露 secret 原文。

## 后续扩展

- 查询路径稳定后，为 `entities`、`tags` 或 `metadata` 补充 JSONB GIN 索引。
- 审计系统落地后，将 Event 状态变化同步写入统一 `audit_logs`，但不替代
  `event_state_transitions`。
- 如果维护 PostgreSQL enum 成本过高，可以在后续 migration 中改为 `text + check constraint`
  或 lookup table。
- 如果需要可靠事件发布，再单独设计 outbox 或 Event Bus message schema。
