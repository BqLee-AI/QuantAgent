# Event Read Model

`quantagent.core.event_read_model` 是管理台标准事件视图的真源边界。

它负责：

- 标准 `Event` 当前状态快照；
- append-only `event_state_transitions` 状态流转摘要；
- Events list/detail 与 Dashboard featured/metrics 查询；
- 幂等 materialization seam，把 RawEvent、`event_intake` routed-event、approval/runtime 摘要写成可查询的标准 Event。

它不负责：

- RawEvent 采集事实、去重和 capture ledger；
- Event Bus topic / publisher / consumer；
- Approval 状态机、Runtime inspect 全量恢复视图；
- API envelope、HTTP 状态码或 FastAPI router。

关系边界：

- RawEvent 仍是采集事实真源；
- `event_intake` routed-event 仍是 AI intake/routing 输出；
- Event read model 是管理台 `/api/v1/events*` 与 `/api/v1/dashboard/summary` 的业务真源；
- Runtime/Approval 只通过引用或脱敏摘要进入这里，不把完整 prompt、provider raw response、secret 或 broker credential 持久化到 Event read model。
