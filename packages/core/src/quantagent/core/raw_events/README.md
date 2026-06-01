# raw_events

`quantagent.core.raw_events` 负责 source 输出进入平台后的第一层持久化边界。

当前职责：

- 校验 `source_plugin_id`、`source_binding_id`、`scheduler_run_id` 的归属关系
- 按平台统一优先级生成 dedupe key
- 把 `SourceFetchResult` 持久化为 `raw_events` canonical row
- 在重复命中时只更新重复计数和最近命中时间，不额外写重复行

明确不放这里的内容：

- Source Plugin 实现细节
- Scheduler loop 编排
- Event 标准化、router、analysis、decision
- API DTO 或前端查询模型

使用入口：

- `RawEventService.persist_source_fetch_result(...)`

为什么 V1 不把重复写成多行：

- #221 当前目标是先稳定“原始输入是否已经见过”这条真源。
- 若把重复抓取全部写成多行，#217 的调度回放和 #224 的后续消费需要先额外筛掉重复，再决定是否继续下游处理。
- 因此 V1 采用 canonical row + `duplicate_count` / `last_seen_at`，后续如需要完整 duplicate hit ledger，再单开 change 扩展。
