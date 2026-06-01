## Why

`docs/design/06-source-plugin-design.md`、`docs/design/07-industry-package-design.md` 和 `docs/design/08-api-and-websocket-design.md` 已经分别定义了 `SourceBinding` 是 pull source 的调度主对象、行业包与 source 插件的连接点，以及 API 应以资源为中心并把副作用收敛到 `actions` 路径。但 issue #215、#216、#217、#220 仍停留在契约、持久化、调度循环和治理面的相邻边界，缺少一份专门收住 `SourceBinding` / `SchedulerRun` V1 REST 资源、字段边界、动作路径和错误语义的 OpenSpec 真源。

如果在这个阶段直接实现 API 或 Web 页面，执行者会各自发明 binding/run DTO、动作路径和状态语义，并把 `effective_config`、ORM 字段或调度内部状态错误地固化为公开契约。本 change 先创建 OpenSpec-only 审查面，给后续 `apps/api`、`packages/core`、`packages/contracts` 和 Plugin Detail 只读治理页一个统一的 V1 协议基线。

## What Changes

- 定义 `SourceBinding` V1 只读 REST 资源族，包括列表、详情和最近调度历史的关联读取边界。
- 定义 `SchedulerRun` V1 只读 REST 资源族，包括列表、详情、与 binding 的关联引用和分页/过滤约束。
- 定义 `pause`、`resume`、`run-now` 三个 binding 动作的 HTTP 路径、接受语义、错误 envelope、幂等语义和审计要求。
- 明确 `retry` 不进入本次 V1 动作承诺，只作为后续扩展保留，不在本 change 中定义公开动作路径。
- 定义 list/detail/action response 的 DTO 分层，禁止直接暴露 ORM model、完整 `effective_config`、secret-bearing payload 或调度引擎内部对象。
- 定义 capability / permission gate、`X-Request-ID`、统一 `ApiResponse<T>`、审计记录和实时通道边界，确保 REST 仍是状态真源。
- 为后续实现约束分层职责：`apps/api` router 保持薄层，状态判断和动作编排下沉到 `packages/core` service / repository seam，scheduler app 不直接成为公开 API 契约真源。

## Capabilities

### New Capabilities

- `source-binding-scheduler-run-api-v1`: 定义 SourceBinding 与 SchedulerRun V1 的只读查询、绑定动作、错误 envelope、权限和审计契约。

### Modified Capabilities

- None.

## Impact

- `apps/api`: 后续需要新增 `/api/v1/source-bindings`、`/api/v1/scheduler-runs` 及相关 `actions` router、schema 和错误映射，但本 PR 不实现代码。
- `packages/core`: 后续需要提供 binding/run query service、action service、repository seam 和审计/权限检查边界，但本 PR 不实现持久化或调度器。
- `packages/contracts`: 后续需要将公开 DTO、枚举和 action response 收敛到跨端契约生成物，但本 PR 不生成任何 artifact。
- `apps/web` / Plugin Detail：后续可以基于同一只读字段集展示 SourceBinding 使用情况和 SchedulerRun 历史，而不自行发明协议。
