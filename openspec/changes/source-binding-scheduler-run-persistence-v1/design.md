## Context

issue #216 要解决的是 scheduler 从“按 plugin 单次触发 demo”走向“围绕 binding 运行”的最小持久化真源。相关真源已经给出几条硬边界：

- `docs/design/06-source-plugin-design.md` 要求 pull source 由统一 scheduler 以 `SourceBinding` 为调度主对象，平台负责 effective config、限流、重试、超时、暂停/恢复和调度结果记录。
- `docs/design/04-database-and-persistence-design.md` 要求结构化字段优先、JSONB 只承接扩展和原始载荷、插件不能直接持有数据库 session、关键状态需要可回放。
- `docs/design/10-deployment-and-runtime-design.md` 要求 `api`、`worker`、`scheduler` 共用数据库结构，scheduler heartbeat 只是健康信息，不替代数据库真源。
- `openspec/changes/plugin-scheduling-v1/**` 已经为单次 trigger 定义了 `PluginRunRecord`、`trigger_type`、`status`、`output_summary`、`error_summary` 等运行语义，但明确把 `SourceBinding` 全量模型和持久化留给后续 change。

本 change 是 core/persistence change，不实现业务代码，但必须给后续 migration、repository、service、scheduler loop、RawEvent 归属和 API 契约提供同一份字段和分层蓝图。

## Goals / Non-Goals

**Goals:**

- 定义 `SourceBinding` 主表的职责：保存相对稳定的绑定元数据、effective config 快照、调度策略、当前状态摘要和最小审计字段。
- 定义 `SchedulerRun` append-only 运行表的职责：保存每次调度尝试的不可变历史，不让 binding 主表替代 run history。
- 定义后续实现的目录与分层边界，让 `packages/core` 承载 ORM、repository 和 service seam，而不是把状态机或 ORM 查询散落在 `apps/scheduler`。
- 收住与 #215 / #217 / #221 / #226 的关联字段和非目标，避免相邻 issue 继续重新定义 `binding_id`、`run_id`、`trigger_mode`、`next_run_at`、`failure_summary`。
- 为后续 `RawEvent` 归属、pause/resume、run-now、scheduler heartbeat 和审计扩展预留稳定接入位点。

**Non-Goals:**

- 不实现 Alembic migration、ORM model、repository、service、scheduler loop 或 API route。
- 不定义 `RawEvent` 表结构、去重细节、Event Bus outbox 或 worker 消费行为。
- 不定义前端 DTO、WebSocket 推送、控制台页面或审批能力。
- 不让插件或 `apps/scheduler` 直接获得数据库 session、ORM model 或持久化写入权限。

## Decisions

### 1. 采用两层持久化模型：`SourceBinding` 主表 + `SchedulerRun` append-only 历史表

决策：

- `SourceBinding` 只承接配置与当前调度状态真源，例如 `owner_type`、`owner_id`、`source_plugin_id`、`source_plugin_version`、`effective_config_snapshot`、`schedule_policy`、`retry_policy`、`rate_limit_policy`、`status`、`last_run_ref`、`last_run_status`、`last_run_at`、`next_run_at`、`last_heartbeat_at`、`disabled_reason`、`created_at`、`updated_at`、`created_by`、`updated_by`。
- `SchedulerRun` 只承接每次尝试的不可变历史，例如 `run_id`、`binding_id`、`source_plugin_id`、`source_plugin_version`、`trigger_mode`、`request_id`、`status`、`attempt_index`、`started_at`、`finished_at`、`duration_ms`、`timeout_ms`、`failure_code`、`failure_message`、`failure_stage`、`retryable`、`output_summary`、`captured_count`、`metadata`、`created_at`。

原因：

- binding 是调度配置和当前摘要的真源；run 是审计和回放的真源。把两者压成一个大表会让高频调度写入和配置真源耦合。
- append-only run history 可以回答“哪次运行失败、是谁触发、何时开始、与哪个 binding 关联”，符合 `packages/core` 和数据库设计中的审计要求。

备选方案：

- 只保留一个 `source_bindings` 大表并覆盖 `last_error`、`last_output` 等字段。放弃原因是会丢失历史尝试、无法支撑 #221 RawEvent 归属和 #226 run 只读 API。

### 2. `SourceBinding` 用稳定摘要字段承接调度热路径，但摘要不替代 run history

决策：

- `SourceBinding` 主表保留读取和调度索引需要的摘要字段：`status`、`last_run_status`、`last_run_at`、`next_run_at`、`last_success_at`、`consecutive_failure_count`、`last_run_id`。
- 这些字段只能作为读取优化和 due binding 查询的热路径索引，不替代 `SchedulerRun` 历史。

原因：

- scheduler loop (#217) 需要高效查询 `next_run_at <= now` 的 active bindings，不能每次从历史表倒推当前状态。
- 同时需要明确这些摘要字段是派生视图，不允许用覆盖式写法替代 run 审计链。

备选方案：

- 完全不在 binding 主表保存 last/next 摘要，只从 run 历史推导。放弃原因是 scheduler due 查询和 API list 代价过高，也违背 issue #216 想要“围绕 binding 运行”的主对象语义。

### 3. `effective_config`、policy 和结果摘要都采用“结构化优先 + JSONB 补充”的字段策略

决策：

- `effective_config_snapshot`、`schedule_policy`、`retry_policy`、`rate_limit_policy`、`output_summary`、`metadata` 使用 JSON-like object 表达，但必须保留关键状态和关联字段的结构化列。
- `effective_config_snapshot` 保存可审计快照，不保存 secret 明文；敏感值只能是 masked value 或 secret reference。
- `failure_message` 只承接脱敏摘要，不保存原始 stack trace、本地绝对路径、token 或 cookie。

原因：

- `docs/design/04` 要求结构化字段优先，JSONB 只补充扩展；高价值查询字段如 `status`、`binding_id`、`run_id`、`trigger_mode` 必须结构化。
- #215 负责合成契约，本 change 只保存“平台已经校验完成的快照”，避免 ORM 再次拥有合成算法所有权。

备选方案：

- 把 entire effective config、policy、failure 和 output 全部塞进 JSONB。放弃原因是后续查询、索引、审计和 API 契约都会失去稳定边界。

### 4. repository / service 边界必须在 core 中表达，调用链固定为 scheduler or API -> service -> repository

目录蓝图：

```text
packages/core/src/quantagent/core/
  db/
    models/
      source_binding.py
      scheduler_run.py
    repositories/
      source_binding_repository.py
      scheduler_run_repository.py
  scheduling/
    binding_models.py
    run_models.py
    binding_service.py
    run_service.py
    README.md

packages/core/tests/
  test_source_binding_repository.py
  test_scheduler_run_repository.py
  test_scheduling_binding_service.py
```

职责：

- `db/models/*.py`：仅做表字段、索引、唯一性和关系声明，不混入业务方法。
- `db/repositories/*.py`：承接 due binding 查询、run append、状态摘要更新和只读查询构造，不承载业务规则。
- `scheduling/*service.py`：承接状态机、摘要回写、非法状态流转保护、审计字段填充和对 `plugin-scheduling-v1` run 语义的适配。
- `apps/scheduler` / `apps/api`：后续只通过 service seam 调用，不直接写 ORM session。
- `README.md`：说明 binding/run 模块职责、入口和不要把 API/插件逻辑放进来。

原因：

- 符合 `packages/core/AGENTS.md`、`core-and-plugin-architecture-gate.md` 和 `engineering-quality-gate.md` 的依赖方向要求。
- 避免 `apps/scheduler` 成为持久化真源或状态机所有者。

备选方案：

- 由 scheduler app 直接拼 ORM 查询和事务。放弃原因是会违反 router/app 薄边界，也无法让 #226 API 和 #217 scheduler 复用同一套行为。

### 5. `owner_type` 在 V1 中保留扩展位，但默认以 industry package 为首个主消费者

决策：

- `owner_type` 与 `owner_id` 必须进入 `SourceBinding` 主表，`owner_type` V1 允许枚举扩展，但首批场景以 industry package 为主。
- spec 不强制只允许 industry，避免未来 runtime private binding 或 strategy-owned binding 重新做破坏性迁移。

原因：

- issue #216 已经把 owner_type 是否只限 industry 作为待确认问题；OpenSpec 应为未来扩展留下兼容位，但不在本轮引入额外 owner-specific 行为。

备选方案：

- V1 把 owner 固定成 `industry_plugin_id` 字段。放弃原因是命名过早绑定单一消费者，后续迁移成本高。

### 6. `SchedulerRun` 与 `plugin-scheduling-v1` 的运行语义对齐，但 `binding_id` 成为新的一级关联位点

决策：

- `SchedulerRun.status`、`trigger_mode`、`timeout_ms`、`output_summary`、`error_summary` 的语义延续 `plugin-scheduling-v1`。
- 新增 `binding_id` 作为一级关联字段；对于 source scheduling 场景，run 不再只靠 `plugin_id + capability` 识别归属。

原因：

- `plugin-scheduling-v1` 已定义通用 run 语义，本 change 不能发明第二套状态机。
- issue #217、#221、#226 都需要稳定的 `binding_id` / `run_id` 关系，单靠 `plugin_id` 无法区分多 owner 复用。

备选方案：

- 为 SourceBinding 场景完全独立一套 run 状态机。放弃原因是会与现有 scheduling change 发生契约漂移。

## Risks / Trade-offs

- [Risk] `SourceBinding` 摘要字段过多，主表会重新变成“历史 + 当前状态”混合体。  
  Mitigation：spec 明确 summary 字段只是派生热路径，不得替代 `SchedulerRun` append-only 历史。

- [Risk] `effective_config_snapshot` 与 #215 的契约漂移。  
  Mitigation：本 change 只引用“已合成并已脱敏的快照”，不重新定义合成算法；实现前需先评审 #215。

- [Risk] `SchedulerRun` 与 #221 RawEvent 归属字段命名不一致。  
  Mitigation：spec 固定使用 `binding_id` / `run_id` 作为一级位点，后续 RawEvent change 只能复用而不能重命名。

- [Risk] `owner_type` 预留扩展后，V1 实现者可能误以为要同时支持多种 owner 行为。  
  Mitigation：tasks 明确本轮只要求字段兼容，不要求实现多 owner 分支逻辑。

- [Risk] 没有在本 change 中描述迁移与索引方向，后续实现仍可能在性能上返工。  
  Mitigation：设计里给出 due binding 查询、run history 读取、唯一性和 append-only 索引方向，后续 implementation PR 必须按这些入口验证。

## Migration Plan

本 PR 为 OpenSpec-only，不执行数据库迁移。后续实现 PR 应按以下顺序推进：

1. 先确认 #215 的模板/effective config 契约已获认可。
2. 在 `packages/core` 增加 ORM model、repository 和 service seam。
3. 增加 Alembic migration，创建 `source_bindings` 与 `scheduler_runs` 及其必要索引。
4. 先以单进程/测试 harness 验证 binding 查询、run append 和摘要回写，再接入 #217 scheduler loop。
5. #221 / #226 只复用本 change 的字段命名与关联位点，不重复设计。

回滚策略：

- 如果后续实现 PR 的 migration 未上线，可直接撤回实现分支。
- 如果 migration 已上线，回滚必须通过新的 Alembic downgrade 或 forward-fix，而不是手改历史迁移。

## Open Questions

- `owner_type` 的稳定枚举集合是否需要在 #216 实现前由维护者明确第一批值，还是先以 `industry` 为主并保留扩展注释。
- `last_heartbeat_at` 是否应保留在 `SourceBinding`，还是由 #217 的 scheduler service 只写全局 heartbeat 而不写 binding 级心跳。
- `attempt_index` 是按单次触发中的 retry 次数递增，还是仅表示 run 在 binding 历史中的序号；默认建议前者，并把历史排序交给 `created_at` / `started_at`。
