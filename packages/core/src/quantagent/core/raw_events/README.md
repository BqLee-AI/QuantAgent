# raw_events

`quantagent.core.raw_events` 负责 source 输出进入平台后的第一层持久化边界。

当前职责：

- 校验 `source_plugin_id`、`source_binding_id`、`scheduler_run_id` 的归属关系
- 按平台统一优先级生成 canonical dedupe key
- 把 `SourceFetchResult` 持久化为 `raw_events` canonical row + `raw_event_captures` ownership ledger
- 在 duplicate 命中时复用 canonical row，并为新的 binding/run 追加 capture 留痕
- 对 `raw_payload` 做脱敏、query 净化和 128 KiB 上限控制

明确不放这里的内容：

- Source Plugin 实现细节
- Scheduler loop 编排
- Event 标准化、router、analysis、decision
- API DTO 或前端查询模型

使用入口：

- `RawEventService.persist_source_fetch_result(...)`

当前双层模型：

- `raw_events` 只保存 canonical source 内容真源，dedupe identity 固定为 `(source_plugin_id, canonical_dedupe_key)`。
- `raw_event_captures` 追加保存每次 binding/run 的 ownership capture，不能被 canonical summary 替代。
- 同一 `run_id` 下命中同一 canonical raw event 时保持幂等，不重复追加 capture。

不要把这些逻辑放到别处：

- scheduler loop 不要自己重算 dedupe 或直接写 ORM
- plugin 不要自定义最终 dedupe key 或绕过 payload 边界
- #224 后续消费只读 canonical RawEvent 与 capture ownership，不在下游重写 dedupe 规则
