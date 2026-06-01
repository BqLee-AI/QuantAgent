## 1. OpenSpec 评审与依赖收口

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `source-binding-scheduler-run-persistence-v1` 的 proposal、design、specs、tasks 和必要 PR 说明。
- [ ] 1.2 在 PR 说明中链接 issue #216，并写清本 PR 只定义持久化模型与分层边界，不实现 migration、ORM、repository、service、scheduler loop、RawEvent 或 API。
- [ ] 1.3 在维护者对 OpenSpec-only PR 明确评论“没问题”或批准前，不进入 `packages/core`、`apps/scheduler`、`apps/api` 或插件实现。
- [ ] 1.4 在实现前人工复核 #215、#217、#221、#226 是否继续复用本 change 的 `binding_id`、`run_id`、`next_run_at`、`trigger_mode` 命名。

## 2. SourceBinding 模型蓝图

- [ ] 2.1 在 `packages/core/src/quantagent/core/db/models/source_binding.py` 规划 `SourceBinding` ORM：`binding_id`、owner 字段、plugin 引用、`effective_config_snapshot`、`schedule_policy`、`retry_policy`、`rate_limit_policy`、`status`、`last_run_id`、`last_run_status`、`last_run_at`、`last_success_at`、`next_run_at`、`consecutive_failure_count`、审计字段。
- [ ] 2.2 为 `SourceBinding` 规划 due 查询与列表读取所需索引，至少覆盖 `status + next_run_at`、owner 查询、plugin 查询和软删除/禁用过滤策略。
- [ ] 2.3 明确 `SourceBinding` 的 secret 与脱敏边界：快照只保存 masked value 或 secret reference，不保存 secret 明文。
- [ ] 2.4 明确 `owner_type` 只作为可扩展字段保留，不要求在 V1 实现多 owner 行为分支。

## 3. SchedulerRun 历史蓝图

- [ ] 3.1 在 `packages/core/src/quantagent/core/db/models/scheduler_run.py` 规划 `SchedulerRun` ORM：`run_id`、`binding_id`、plugin 引用、`trigger_mode`、`request_id`、`status`、`attempt_index`、`started_at`、`finished_at`、`duration_ms`、`timeout_ms`、`captured_count`、`output_summary`、`failure_code`、`failure_message`、`failure_stage`、`retryable`、`metadata`、审计字段。
- [ ] 3.2 明确 `SchedulerRun` 采用 append-only 历史策略；允许更新同一 run 的进行中到终态字段，但不得覆盖或删除已完成历史记录。
- [ ] 3.3 规划 `binding_id + started_at`、`binding_id + created_at`、`request_id`、`status` 等读取入口的索引方向，并说明哪些字段是只读查询热路径。
- [ ] 3.4 对齐 `plugin-scheduling-v1` 的 run 状态和错误摘要语义，不重新发明第二套状态机。

## 4. Repository / Service 分层

- [ ] 4.1 在 `packages/core/src/quantagent/core/db/repositories/` 规划 `SourceBindingRepository` 与 `SchedulerRunRepository`，只承接 ORM 查询、过滤、分页和事务内写入。
- [ ] 4.2 在 `packages/core/src/quantagent/core/scheduling/` 规划 `binding_service.py` 与 `run_service.py`，承接 due binding 查询、run append、摘要回写、非法状态流转保护和最小审计填充。
- [ ] 4.3 在 `packages/core/src/quantagent/core/scheduling/README.md` 记录模块职责、入口、不要放什么，并用中文说明 binding 主表与 run 历史的分工。
- [ ] 4.4 明确后续 `apps/scheduler`、`apps/api` 只能通过 service seam 访问持久化，不直接操作 ORM session 或插件实现。

## 5. 验证与实现前门槛

- [ ] 5.1 运行 `openspec validate source-binding-scheduler-run-persistence-v1 --type change --strict --json`。
- [ ] 5.2 后续实现 PR 至少验证 due binding 查询、run append、run failed/timeout 脱敏摘要和 binding 摘要回写。
- [ ] 5.3 后续实现 PR 至少验证 `SourceBinding` 与 `SchedulerRun` 不作为 API DTO 或 plugin DTO 直接暴露。
- [ ] 5.4 后续实现 PR 至少验证与 #221 RawEvent、#226 API 契约复用同一 `binding_id` / `run_id` 关联位点。
