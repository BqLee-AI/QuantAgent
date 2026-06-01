# scheduling

该目录承接 SourceBinding 与 SchedulerRun 的 core 调度边界。

职责：

- `models.py` 保留通用调度 run/request DTO 与状态枚举。
- `binding_models.py` / `run_models.py` 表达 binding/run 的领域输入输出，不暴露 ORM。
- `binding_service.py` / `run_service.py` 承接状态机、摘要回写、最小审计字段和失败路径保护。
- `loop_service.py` 承接 SourceBinding interval loop 编排：扫描 due bindings、调用 runtime、落 `SchedulerRun`、回写 `next_run_at`，但不管理进程生命周期。
- `query_service.py` 提供 SourceBinding / SchedulerRun 的只读查询入口，给 API 读模型使用。
- `action_service.py` 提供 `pause` / `resume` / `run-now` 的动作编排入口，但不承接 scheduler loop。
- `repository.py` / `service.py` 保留已有 plugin-scheduling-v1 单次触发能力。

不要放什么：

- 不放 API DTO、HTTP 语义或前端展示字段。
- 不让插件直接访问 ORM model 或数据库 session。
- 不把 scheduler app 的 loop、sleep、进程控制塞进 core service。

边界说明：

- `SourceBinding` 主表是配置真源和当前调度摘要真源。
- `SchedulerRun` 是 append-only 的调度历史真源。
- `last_*` / `next_*` 只服务 due 查询和只读摘要，不能替代 run 历史。
- interval loop 只支持单进程 fixed tick + due binding 扫描；分布式锁、复杂 retry/backoff、RawEvent 持久化与 worker routing 不属于这里。
