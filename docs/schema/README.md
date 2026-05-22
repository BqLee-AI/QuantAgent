# Schema 设计索引

## 文档范围

本目录保存 QuantAgent 初版数据库 schema 设计。文档按业务边界拆分，作为后续
SQLAlchemy ORM model、Alembic migration、repository 和 API DTO 设计的输入。

当前 schema 文档：

| 分组 | 文档 | 表 |
| --- | --- | --- |
| Event | [event-schema.md](event-schema.md) | `raw_events`、`events`、`event_state_transitions` |
| Plugin | [plugin-schema.md](plugin-schema.md) | `plugin_records`、`plugin_versions`、`plugin_configs`、`plugin_dependency_records` |
| Analysis | [analysis-schema.md](analysis-schema.md) | `agent_runs`、`agent_run_steps`、`tool_invocations`、`routing_decisions`、`industry_analyses`、`scored_analyses`、`decision_results` |
| Human / Notification | [human-notification-schema.md](human-notification-schema.md) | `approval_records`、`notification_records` |
| Audit / Runtime | [audit-runtime-schema.md](audit-runtime-schema.md) | `audit_logs`、`runtime_errors` |

## 落地顺序

推荐 migration 落地顺序：

1. Event 表与 `event_status`。
2. Plugin 表。
3. Analysis 表。
4. Human / Notification 表。
5. Audit / Runtime 表。

原因：

- 大多数表依赖 `events.id`。
- Analysis 表依赖 Event 表。
- Human / Notification 表依赖 Decision、Tool invocation 和 Event。
- Audit / Runtime 表依赖多个业务对象，适合最后落地。

## Enum 策略

PostgreSQL enum 后续改值成本较高。初版建议：

- `event_status` 可以使用 PostgreSQL enum，因为它是核心状态机字段且相对稳定。
- 其他状态、类型、动作和渠道字段在文档中统一写为 `text`，约束说明为“按某某值约束”；落地时优先使用 `text + check constraint` 或 service 层校验。
- `audit_logs.action` 使用 `text`，按 `<domain>.<action>` 命名，不使用 PostgreSQL enum。
- 如果某个状态集合稳定后需要更强 DB 约束，再通过后续 migration 收紧。

## 外键与循环关系

默认原则：

- 历史、审计、状态流转相关表优先 `on delete restrict` 或保留历史。
- 可从主流程恢复的引用可以 `on delete set null`。
- 避免双向 nullable 外键和循环外键。

已知特殊关系：

- `plugin_records.active_version_id` 逻辑引用 `plugin_versions.id`，但与
  `plugin_versions.plugin_record_id` 形成循环。初版建议不建数据库外键，由 Registry/service
  事务保证；如果后续需要 DB 约束，使用 nullable 后置更新和 deferrable FK。
- `notification_records` 不保存 `runtime_error_id`；通知错误由
  `runtime_errors.notification_record_id` 或 `trace_id` 关联，避免双向关系漂移。

## 数据保留与删除

- `event_state_transitions` 和 `audit_logs` 是 append-only，不更新、不删除业务历史。
- `events` 使用 soft delete，保留事件状态、分析、审批、通知和审计链。
- `plugin_records` 使用 soft delete，设置 `status = uninstalled` 和 `uninstalled_at`。
- `plugin_configs` 使用归档语义，设置 `status = archived` 和 `archived_at`。
- 真实物理删除只允许用于本地开发或明确的维护脚本。

## 敏感信息

所有 schema 共同遵守：

- 不保存真实 secret、token、cookie、session、签名、口令、数据库连接串或完整敏感工具参数。
- 需要保存敏感配置时优先保存 `secret://...` 引用。
- 确实必须入库的敏感值需要先加密。
- API、日志、测试断言和通知 payload 不得输出敏感值原文。
- 完整模型推理链、完整 provider 原始响应和大规模网页快照不进入初版主线。
