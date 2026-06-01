## ADDED Requirements

### Requirement: SourceBinding V1 保存 binding 配置真源与调度摘要
The system SHALL persist `SourceBinding` as the scheduler-owned source binding record instead of deriving scheduling state from naked plugin ids or ad hoc config blobs.

#### Scenario: SourceBinding 记录 owner 与 source 引用
- **WHEN** 平台为 pull source 创建一个可调度 binding
- **THEN** `SourceBinding` 记录 MUST 包含唯一 `binding_id`
- **AND** `SourceBinding` 记录 MUST 包含 `owner_type` 与 `owner_id`
- **AND** `SourceBinding` 记录 MUST 包含 `source_plugin_id`
- **AND** `SourceBinding` 记录可以包含 `source_plugin_version`
- **AND** 该记录 MUST 与裸 `source_plugin_id` 调度对象区分开

#### Scenario: SourceBinding 保存 effective config 与 policy 快照
- **WHEN** 平台保存一个可运行的 binding
- **THEN** `SourceBinding` 记录 MUST 保存校验后的 `effective_config_snapshot`
- **AND** `SourceBinding` 记录 MUST 保存 `schedule_policy`
- **AND** `SourceBinding` 记录 MUST 保存 `retry_policy`
- **AND** `SourceBinding` 记录 MUST 保存 `rate_limit_policy`
- **AND** 这些字段 MUST 只包含 JSON-safe 值
- **AND** 这些字段 MUST NOT 保存 secret 明文

#### Scenario: SourceBinding 保存调度热路径摘要
- **WHEN** scheduler 或 API 读取当前 binding 状态
- **THEN** `SourceBinding` 记录 MUST 可提供 `status`
- **AND** `SourceBinding` 记录 MUST 可提供 `last_run_status`
- **AND** `SourceBinding` 记录 MUST 可提供 `last_run_at`
- **AND** `SourceBinding` 记录 MUST 可提供 `next_run_at`
- **AND** `SourceBinding` 记录可以提供 `last_run_id`、`last_success_at` 与 `consecutive_failure_count`
- **AND** 这些摘要字段 MUST NOT 替代 append-only `SchedulerRun` 历史

### Requirement: SchedulerRun V1 以 append-only 方式保存每次调度尝试
The system SHALL persist every scheduler attempt as an append-only `SchedulerRun` record that is linked to a `SourceBinding`.

#### Scenario: SchedulerRun 保存最小运行审计字段
- **WHEN** 平台创建一次 source scheduler run
- **THEN** `SchedulerRun` 记录 MUST 包含唯一 `run_id`
- **AND** `SchedulerRun` 记录 MUST 包含 `binding_id`
- **AND** `SchedulerRun` 记录 MUST 包含 `source_plugin_id`
- **AND** `SchedulerRun` 记录可以包含 `source_plugin_version`
- **AND** `SchedulerRun` 记录 MUST 包含 `trigger_mode`
- **AND** `SchedulerRun` 记录 MUST 包含 `request_id`
- **AND** `SchedulerRun` 记录 MUST 包含 `status`
- **AND** `SchedulerRun` 记录 MUST 包含 `started_at`、`finished_at` 与 `duration_ms`
- **AND** `SchedulerRun` 记录可以包含 `timeout_ms`、`attempt_index`、`captured_count`、`output_summary` 与 `metadata`

#### Scenario: SchedulerRun 失败摘要必须结构化且脱敏
- **WHEN** 一次 scheduler run 失败或超时
- **THEN** `SchedulerRun` 记录 MUST 可保存 `failure_code`
- **AND** `SchedulerRun` 记录 MUST 可保存 `failure_message`
- **AND** `SchedulerRun` 记录 MUST 可保存 `failure_stage`
- **AND** `SchedulerRun` 记录可以保存 `retryable`
- **AND** 失败摘要 MUST NOT 暴露 secret、token、cookie、完整 stack trace 或宿主绝对路径

#### Scenario: SchedulerRun 历史只追加不覆盖
- **WHEN** 同一个 binding 发生多次调度尝试
- **THEN** 平台 MUST 为每次尝试创建新的 `SchedulerRun`
- **AND** 平台 MUST NOT 通过更新旧 run 记录来抹掉已完成的历史尝试
- **AND** `SourceBinding` 主表上的 `last_*` 或 `next_*` 摘要字段 MUST 只反映当前视图

### Requirement: Binding 与 run 持久化只能通过 core repository 与 service seam 访问
The system SHALL keep `SourceBinding` and `SchedulerRun` persistence behind core repository and service boundaries instead of letting apps or plugins directly own ORM access.

#### Scenario: scheduler app 通过 core service 操作 binding 与 run
- **WHEN** `apps/scheduler` 查询 due bindings、写入 run started 或更新 run finished
- **THEN** 调用链 MUST 经过 `packages/core` 的 scheduling service
- **AND** scheduling service MUST 依赖 repository seam
- **AND** `apps/scheduler` MUST NOT 直接拼接 ORM 查询或直接持有数据库 session

#### Scenario: API 与插件不能直接写 binding/run ORM
- **WHEN** API 动作或插件执行需要影响 binding 或 run 状态
- **THEN** API router MUST 通过 core service 调用
- **AND** 插件 MUST NOT 直接访问 `SourceBinding` 或 `SchedulerRun` ORM model
- **AND** 插件 MUST NOT 直接持有数据库 session

### Requirement: Binding 与 run 字段为相邻 change 提供稳定关联位点
The system SHALL expose stable persistence identifiers so adjacent changes can reuse them for scheduler loops, RawEvent ownership, and API contracts.

#### Scenario: scheduler loop 复用 binding 主对象与 run 历史
- **WHEN** issue #217 实现 interval loop
- **THEN** due binding 查询 MUST 以 `binding_id`、`status` 与 `next_run_at` 为核心位点
- **AND** loop 写入历史 MUST 复用 `SchedulerRun.run_id`
- **AND** loop MUST NOT 重新发明另一套 binding identity 或 run history 字段命名

#### Scenario: RawEvent 与 API 复用 binding/run 引用
- **WHEN** issue #221 或 #226 需要表达调度归属
- **THEN** 这些能力 MUST 复用 `binding_id` 与 `run_id` 作为一级关联字段
- **AND** 它们 MUST NOT 要求 `SourceBinding` 或 `SchedulerRun` 暴露 ORM model 作为外部 DTO
- **AND** 它们 MUST NOT 通过插件私有字段重新表达同一归属关系
