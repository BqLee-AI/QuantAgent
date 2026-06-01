## 1. OpenSpec 审查门

- [x] 1.1 创建 `source-binding-scheduler-run-api-contract-v1` change，并只写入本 change 的 proposal、design、tasks、spec。
- [x] 1.2 在 OpenSpec 中明确本轮只定义 `SourceBinding` / `SchedulerRun` V1 只读与基础动作契约，不实现业务代码。
- [x] 1.3 提交 OpenSpec-only PR，PR 说明链接 issue #226，并写明 `retry` 不进入本次 V1 动作承诺。
- [x] 1.4 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. API 契约实现切片

- [x] 2.1 在 `apps/api` 定义 `source-bindings` 的 request/response schema，并让 binding 关联 run 历史复用既有 Runtime Inspect `scheduler-runs` 公开模型，保持 DTO 与 ORM / plugin DTO 分层。
- [x] 2.2 在 `apps/api` 增加 `GET /api/v1/source-bindings`、`GET /api/v1/source-bindings/{binding_id}`、`GET /api/v1/source-bindings/{binding_id}/scheduler-runs` router，并统一走 `ApiResponse[T]`。
- [x] 2.3 不在本 change 中定义第二套 `GET /api/v1/scheduler-runs*` router；全局 `scheduler-runs` 公开资源复用 Runtime Inspect 已合并接口，本 change 只保留 binding-scoped 关联语义。
- [x] 2.4 在 `apps/api` 增加 binding actions router：`pause`、`resume`、`run-now`，并把非法状态流转映射到稳定错误码。

## 3. Core service 与 repository seam

- [x] 3.1 在 `packages/core` 定义 `SourceBindingQueryService` 与 `SchedulerRunQueryService` 的查询边界，避免 router 直接访问 ORM。
- [x] 3.2 在 `packages/core` 定义 `SourceBindingActionService` 与 scheduler dispatch port 的接口边界，收住 `pause`、`resume`、`run-now` 的业务编排。
- [x] 3.3 定义 query repository / action repository 所需的最小读写接口，复用 #216 的持久化模型而不反向耦合 API DTO。
- [x] 3.4 明确 capability gate、审计记录写入和 request id 透传的 service 责任。

## 4. 契约联动与验证

- [x] 4.1 将 `source-bindings` 公开 DTO、枚举和 action response 同步到 `packages/contracts` 或等价生成真源，并明确 run 历史关联字段复用 Runtime Inspect `scheduler-runs` 模型，避免前端自行发明字段。
- [x] 4.2 为 API 路由添加最小测试，覆盖 envelope、not found、permission denied、非法状态流转和 `run-now accepted` 语义。
- [x] 4.3 为 core service 添加最小测试，覆盖 `pause`/`resume` 幂等、`run-now` 审计写入和 capability 拒绝路径。
- [x] 4.4 运行 `openspec validate source-binding-scheduler-run-api-contract-v1 --type change --strict --json`，并在实现 PR 中补充 API 测试结果。
