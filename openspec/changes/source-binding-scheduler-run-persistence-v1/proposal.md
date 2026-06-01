## Why

`docs/design/06-source-plugin-design.md` 已把 `SourceBinding` 定义为 pull 类 source 的调度主对象，并要求平台记录每次调度结果；`docs/design/04-database-and-persistence-design.md` 与 `docs/design/10-deployment-and-runtime-design.md` 又把数据库和独立 scheduler 入口明确为运行时真源的一部分。当前 issue #215 只收住模板与 effective config 契约，issue #217 / #221 / #226 又分别依赖 binding 真源、run 历史和稳定关联位点，因此必须先为 issue #216 定义 `SourceBinding` 与 `SchedulerRun` 的 V1 持久化边界。

如果没有这层持久化模型，后续实现会在 scheduler loop、RawEvent 归属、API DTO 和行业包复用之间各自发明字段、状态机和审计语义，最终破坏 core/service/repository 分层以及 append-only 运行历史要求。

## What Changes

- 定义 `SourceBinding` V1 持久化能力，收住 owner 归属、source plugin 引用、effective config 快照、schedule/retry/rate-limit policy、当前调度状态摘要和最小审计字段。
- 定义 `SchedulerRun` V1 append-only 运行记录能力，收住 run identity、binding/plugin 归属、触发方式、开始/结束时间、状态、失败摘要、attempt 索引和结果摘要。
- 定义 `SourceBinding` 与 `SchedulerRun` 的 repository / service 边界，要求 scheduler、API 和插件只能通过 core seam 访问持久化真源。
- 明确与 issue #215、#217、#221、#226 的衔接边界，保证 binding/run 字段命名、关联位点和非目标一致。
- 明确本 change 只产出 OpenSpec，不实现 migration、ORM、repository、service、API 或 scheduler loop。

## Capabilities

### New Capabilities
- `source-binding-scheduler-run-persistence`: 定义 `SourceBinding` 与 `SchedulerRun` 的 V1 持久化模型、状态边界、append-only run history 和 core repository/service 契约。

### Modified Capabilities
- None.

## Impact

- 受影响真源：issue #216、#215、#217、#221、#226，`docs/design/04-database-and-persistence-design.md`，`docs/design/06-source-plugin-design.md`，`docs/design/10-deployment-and-runtime-design.md`，`openspec/changes/plugin-scheduling-v1/**`。
- 受影响实现边界：后续实现预计落在 `packages/core/src/quantagent/core/db/models/`、`packages/core/src/quantagent/core/db/repositories/`、`packages/core/src/quantagent/core/scheduling/`，以及依赖这些 seam 的 `apps/scheduler` / `apps/api`。
- 无新增依赖、无实现代码、无 API/前端改动；本 PR 仅新增 `openspec/changes/source-binding-scheduler-run-persistence-v1/`。
